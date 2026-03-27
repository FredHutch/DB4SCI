"""
Docker Swarm utility functions for MyDB

This module contains functions for managing Docker Swarm services.
"""

import base64
import json
import sys
import time

import docker
from docker.errors import APIError, NotFound
from docker.types import ConfigReference, EndpointSpec, Mount, RestartPolicy, DriverConfig

from . import admin_db, mydb_config
from .human import human_uptime
from .send_mail import send_mail

# Initialize Docker client
client = docker.from_env()


def display_volume_list():
    volumes = volume_list()
    header = "{:<40} {:<10} {}".format("Volume", "Driver", "Created")
    body = ""
    for volume in volumes:
        if "mydb" in volume["name"]:
            up_time = human_uptime(volume["created"])
            body += f"{volume['name']:<40} {volume['driver']:<10} {up_time}\n"
    return header, body


def volume_list():
    """list all volumes using docker system df for size information"""
    volumes = client.volumes.list()

    volume_info = []
    for volume in volumes:
        volume_info.append(
            {
                "name": volume.attrs["Name"],
                "driver": volume.attrs["Driver"],
                "created": volume.attrs["CreatedAt"],
            }
        )
    return volume_info


def create_volume_directory(vname):
    """
    When creating an NFS-backed volume, the directory
    that it points to must exist. This will create a container
    that points to the parent of the desired volume, and
    create the directory inside it.
    """
    # First, see if the parent volume already exists:
    parent_vol = [x for x in client.volumes.list() if x.name == "nfs_root"]
    if not parent_vol:
        # Otherwise, create it:
        parent_vol = client.volumes.create(
            name="nfs_root",
            driver="local",
            driver_opts={
                "type": "nfs",
                "o": f"addr={mydb_config.NFS_HOST},rw",
                "device": f":{mydb_config.NFS_ROOT_PATH}/",  # Mount the root
            },
        )

    client.containers.run(
        "alpine",
        f"mkdir -p /mnt/{vname}",
        volumes={"nfs_root": {"bind": "/mnt", "mode": "rw"}},
        remove=True,
    )
    print(f"create_volume_directory: Created directory {vname}....")

def remove_volume_data(vname):
    """
    The "opposite" of create_volume_directory().
    Removes the data on the NFS-backed store.
    Should be called after the volume has been removed.
    """
    # First, see if the parent volume already exists:
    parent_vol = [x for x in client.volumes.list() if x.name == "nfs_root"]
    if not parent_vol:
        # Otherwise, create it:
        parent_vol = client.volumes.create(
            name="nfs_root",
            driver="local",
            driver_opts={
                "type": "nfs",
                "o": f"addr={mydb_config.NFS_HOST},rw",
                "device": f":{mydb_config.NFS_ROOT_PATH}/",  # Mount the root
            },
        )

    client.containers.run(
        "alpine",
        f"rm -rf  /mnt/{vname}",
        volumes={"nfs_root": {"bind": "/mnt", "mode": "rw"}},
        remove=True,
    )
    return f"remove_volume_data: Removed directory {vname}...."



def create_docker_volume(vname):
    """create a volume if it does not exist
    Returns: (volume_id, error) tuple
        - If successful: (volume_id, None)
        - If error: (None, error_message)
    """
    # TODO FIXME stop calling me!
    if True:
        return None, None
    try:
        volume = client.volumes.get(vname)
        return volume.id, None  # Volume already exists, no error
    except docker.errors.NotFound:
        try:
            create_volume_directory(vname)
            volume = client.volumes.create(
                name=vname,
                driver="local",
                driver_opts={
                    "type": "nfs",
                    "o": f"addr={mydb_config.NFS_HOST},rw",
                    "device": f":{mydb_config.NFS_ROOT_PATH}/{vname}",
                },
            )
            return volume.id, None  # Volume created successfully, no error
        except docker.errors.APIError as e:
            return None, f"Error creating volume: {e}"
    except docker.errors.APIError as e:
        return None, f"Error checking volume: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def volume_remove(vname):
    """Remove a docker volume
    volume remove typically fails until the service is fully removed.
    Try to remove for a few times before giving up"""
    # TODO should we also remove the underlying directory on NFS storage?
    # i.e., the opposite of create_volume_directory()?
    # ---
    client = docker.from_env()

    # 1. Define a 'Task' to remove the specific volume
    # We use a shell command to check if it exists first to avoid exit errors
    cleanup_cmd = f"sh -c 'docker volume rm {vname} || true'"

    print(f"Deploying global cleanup for {vname}...")

    client.services.create(
        image="docker:latest", # Use the docker CLI image
        name="volume-cleanup-global",
        command=cleanup_cmd,
        mounts=[
            # This gives the container on EACH node access to its own local engine
            Mount(target='/var/run/docker.sock', source='/var/run/docker.sock', type='bind')
        ],
        mode={'global': {}} # Runs on EVERY node in the cluster
    )

    # 2. Wait for the tasks to complete
    # In a global service, it starts one task per node.
    # We'll wait a few seconds for them to pull the image and run the command.
    time.sleep(15)
    mesg = f"Docker Volume {vname} removed."
    return mesg


def create_config(params, config, target_path=None):
    """Create Docker Swarm config for service initialization

    Args:
        params: Dictionary containing config_name and other parameters
        config: String content of the config file
        target_path: Optional path where config should be mounted in container.
                    Defaults to /docker-entrypoint-initdb.d/init.sql for PostgreSQL

    Returns:
        List of ConfigReference objects or None on error
    """
    if target_path is None:
        target_path = "/docker-entrypoint-initdb.d/init.sql"

    try:
        config_obj = client.configs.create(
            name=params["config_name"], data=config.encode("utf-8")
        )
    except docker.errors.APIError as e:
        print(f"create_config: error: {e}", file=sys.stderr)
        return None
    params["config_id"] = config_obj.id
    config_ref = [
        ConfigReference(
            config_id=config_obj.id,
            config_name=params["config_name"],
            filename=target_path,
            uid="999",
            gid="999",
            mode=0o555,
        )
    ]
    return config_ref


def start_service(params, config_ref):
    # Create docker service
    params_json = json.dumps(params, indent=4)
    print(f"====DEBUG: swarm_util.start_service: params: {params_json}")
    nfs_config = DriverConfig(
        name='local',
        options={
            'type': 'nfs',
            'o': f'addr={mydb_config.NFS_HOST}',
            'device': f':{mydb_config.NFS_ROOT_PATH}/{params["volume_name"]}',
        }
    )
    print(f"Creating volume directory {params['volume_name']}")
    create_volume_directory(params['volume_name'])

    service = client.services.create(
        image=params["image"],
        name=params["service_name"],
        user=params["service_user"],
        env=params["env"],
        mounts=[
            Mount(
                target=params["mapped_db_vol"],
                source=f"{params['volume_name']}",
                type="volume",
                driver_config=nfs_config,
            ),
            {  # ← Use dict for tmpfs
                "Target": "/dev/shm",
                "Type": "tmpfs",
                "TmpfsOptions": {"SizeBytes": 1073741824, "Mode": 1777},
            },
        ],
        configs=config_ref,
        endpoint_spec=EndpointSpec(ports={int(params["Port"]): params["default_port"]}),
        restart_policy=RestartPolicy(condition="any"),
        labels=params["labels"],
    )

    time.sleep(1)
    # Basic attributes
    print(f"Service ID: {service.id}")
    print(f"Service Name: {service.name}")
    print(f"Service short ID: {service.short_id}")

    # Wait for service to have running tasks
    timeout = 30  # seconds
    start_time = time.time()

    while time.time() - start_time < timeout:
        service.reload()
        tasks = service.tasks()
        if tasks:
            task = tasks[0]
            if task["Status"]["State"] == "running":
                print(f"Service {params['Name']} is running")
                c_id = admin_db.add_service(service, params)
                return service, "Service Started"
            elif task["Status"]["State"] in ["failed", "shutdown", "rejected"]:
                error_msg = task["Status"].get("Err", "Unknown error")
                send_mail(
                    "MyDB: service failed to start",
                    f"Service {params['Name']} failed: {error_msg}",
                    mydb_config.supportAdmin,
                )
                return (
                    None,
                    f"Service failed to start. State: {task['Status']['State']}, Error: {error_msg}",
                )
        time.sleep(0.5)

    return None, f"Service did not start within {timeout} seconds."


def stop_remove(service_name):
    """Stop and remove a docker swarm service
    In Swarm, services don't need to be "stopped" - removing them
    automatically stops all tasks.

    Args:
        service_name: Name of the service to remove

    Returns:
        True if successful
        Error message string if failed

    Note:
        This should not be accessed directly, but from kill_service()
        kill_service will cleanup the admin_db
    """
    try:
        service = client.services.get(service_name)
    except docker.errors.NotFound:
        msg = f"Error: Service not found: {service_name}"
        print(msg)
        return msg
    except docker.errors.APIError as e:
        msg = f"Error: API error getting service {service_name}: {e}"
        print(msg)
        return msg

    try:
        service.remove()
        msg = f"Service {service_name} removed successfully"
        return msg
    except docker.errors.APIError as e:
        msg = f"Error: removing service {service_name}: {e}"
        print(msg)
        return msg


def restart_service(name):
    """Restart a Docker Swarm service by forcing an update

    In Docker Swarm, there's no direct "restart" command. Instead,
    we use service.update(force_update=True) which recreates the
    service's tasks (containers), effectively restarting them.

    This is important for database configuration changes that require
    a restart to take effect (e.g., ALTER SYSTEM in PostgreSQL,
    SET PERSIST in MariaDB).

    Args:
        name: Container name (not service name - we'll look up the service)

    Returns:
        String message indicating success or error
    """
    state_info = admin_db.get_container_state(name)
    if state_info is None:
        return f"Error: Container '{name}' not found in Admin DB"

    data = admin_db.get_container_data("", c_id=state_info.c_id)
    if "Info" not in data or "service_name" not in data["Info"]:
        return f"Error: Service name not found for container '{name}'"

    service_name = data["Info"]["service_name"]

    try:
        service = client.services.get(service_name)
    except docker.errors.NotFound:
        return f"Error: Service '{service_name}' not found"
    except docker.errors.APIError as e:
        return f"Error: API error getting service '{service_name}': {e}"

    try:
        # Force update with no changes - this recreates tasks (restarts)
        service.update(force_update=True)
        return f"Service '{name}' restarted successfully"
    except docker.errors.APIError as e:
        return f"Error: Failed to restart service '{service_name}': {e}"


def admin_delete(name, username):
    """Stop and remove docker service
    Remove volumes and configs associated with the service
    Args:
        name: Name of the service to remove
        username: Admin username performing the action

    Returns:
        String describing the results of the operation
    """
    result = f"Admin action requested: delete service: {name} "
    result += f"Requested by {username}\n"

    state_info = admin_db.get_container_state(name)
    if state_info is None:
        return f"unable to find {name} in Admin DB"
    data = admin_db.get_container_data("", c_id=state_info.c_id)
    admin_db.delete_container_state(state_info.c_id)
    description = (
        f"removed {name} by user {username} from admindb (CID: {state_info.c_id})\n"
    )
    admin_db.add_container_log(state_info.c_id, name, "deleted", description)
    result += description

    status = stop_remove(data["Info"]["service_name"])
    if status[:6] == "Error:":
        return result + status + "\n"
    result += status


    status = docker_config_remove(data["Info"]["config_name"])
    result += f"\n{status}"

    status = volume_remove(data["Info"]["volume_name"])
    result += "\n" + status

    status = remove_volume_data(data["Info"]["volume_name"])
    result += "\n" + status

    send_mail("DBaaS: service removed", result, mydb_config.supportAdmin)

    return result


def remove_service(service_name):
    try:
        status = client.service.remove(service_name)
    except docker.errors.NotFound as e:
        return "Error"  # jfdey make better
    return True


def inspect_service(service_name) -> dict:
    """return service meta data.
    Exmple field: insp.attrs['Spec']['Name']
    insp.attrs['Spec']['EndpointSpec']['Ports'][0]['PublishedPort']
    """
    insp = client.services.get(service_name)
    return insp.attrs


def service_exists(service_name):
    try:
        client.services.get(service_name)
    except docker.errors.NotFound:
        return None
    return True


def docker_config_remove(config_name):
    """remove the Docker Swarm config for a container"""
    try:
        config = client.configs.get(config_name)
        if config:
            config.remove()
            return f"Docker Config {config_name} removed."
    except NotFound:
        return f"Docker config not found."
    except APIError as e:
        return f"Error occurered while removing {config_name}: {e}"


def display_services():
    """{"ID":"yv7ds8clfb86","Image":"postgres:17.4","Mode":"replicated","Name":"mydb_admin_db","Ports":"*:32009-\u003e5432/tcp","Replicas":"1/1"}"""
    fields = ["ID", "Name", "Mode", "Image", "Ports", "Status", "Up Time"]
    format_string = "{:<25} {:<25} {:<10} {:<20} {:<12} {:<8} {}"
    header = format_string.format(*fields)
    # Get services filtered by name
    services = client.services.list(filters={"name": "mydb"})

    # Convert to list of dictionaries
    body = ""
    for service in services:
        attrs = service.attrs
        target = attrs["Endpoint"]["Ports"][0]["TargetPort"]
        published = attrs["Endpoint"]["Ports"][0]["PublishedPort"]
        mapping = f"{target}:{published}"
        image = attrs["Spec"]["TaskTemplate"]["ContainerSpec"]["Image"].split("@")[0]
        tasks = service.tasks()
        status = tasks[0]["Status"]["State"]
        up_time = human_uptime(attrs["CreatedAt"])
        # Extract relevant information (docker service ls output)
        line = format_string.format(
            service.id,
            service.name,
            list(attrs["Spec"]["Mode"].keys())[0],  # 'Replicated' or 'Global'
            image,
            mapping,
            status,
            up_time,
        )
        body += line + "\n"
    return header, body
