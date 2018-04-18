#!/usr/bin/python
import os
from io import BytesIO
import tarfile
import time
import errno
import json
import docker
from send_mail import send_mail
from format_fill import format_fill 
import postgres_util
import mongodb_util
import mariadb_util
import neo4j_util
import admin_db
import local_config
from human_uptime import human_uptime


client = docker.Client(base_url='unix://var/run/docker.sock') 
#client = docker.APIClient(base_url='unix://var/run/docker.sock') 

class Notfound(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


def display_containers():
    """List all running containers as reported by docker ps
    return sting data formated for html display
    return: tuple (header, body)
    """
    try:
        containers = client.containers()
    except Exception, e:
        print('Error: postgres_list; client.continers(); error: %s', e)
        return "An error occured: %s" % e

    widths = (22, 22, 6,22, 30, 10, 30, 30)
    header = ("Container", "Username", "Port", "Owner", "Contact", "Status",
              "Image", "Created")
    db_header = format_fill('left',header, widths)
    db_list = ""
    for con in containers:
        if 'Labels' in con and 'DBaaS' in con['Labels'] and (
           con['Labels']['DBaaS'] == 'true'):
            Name = con['Names'][0][1:]
            if 'PublicPort' in con['Ports'][0]:
                port1 = con['Ports'][0]['PublicPort']
            else:
                prt1 = '?'
            if len(con['Ports']) == 2:
                port2 = con['Ports'][1]['PublicPort']
                if port2 > port1:
                    port = str(port1) + ':' + str(port2)
                else:
                    port = str(port2) + ':' + str(port1)
            else:
                port = str(port1)
            if 'OWNER' in con['Labels']:
                owner = con['Labels']['OWNER']
            else:
                owner = ''
            if 'CONTACT' in con['Labels']:
                contact = con['Labels']['CONTACT']  # email
            else:
                contact = ''
            image = con['Image']
            insp = client.inspect_container(con['Names'][0])
            status = insp['State']['Status']
            envs = insp['Config']['Env']
            started = insp['State']['StartedAt']
            human = human_uptime(started)
            user = 'NA'
            for env in envs:
                if 'POSTGRES_USER' in env:
                    user = env.split('=')[1]
                    break
                elif 'DB_USER' in env:
                    user = env.split('=')[1]
                    break
            if 'Memory' in insp['HostConfig']:
                memlimit = "%sMB" % (insp['HostConfig']['Memory'] / 1024 / 1024)
            else:
                memlimit = "None"
            row = ( Name, user, port, owner, contact, status, image, human)
            db_list += format_fill('left', row, widths)
    return db_header, db_list


def exec_command(dbname, command):
    """ Run <command> on container <dbname>
    """
    try:
        insp = client.inspect_container(dbname)
    except docker.errors.NotFound:
        msg = 'Error: exec_command client.inspect_containter; %s' % dbname
        print(msg)
        return msg
    client.start(insp['Id'])
    exe = client.exec_create(container=insp['Id'], cmd=command)
    exe_start = client.exec_start(exec_id=exe, stream=True)

    result = ''
    for val in exe_start:
        result += val
    return result


def get_ports():
    """ return list of ports that are in use
    """
    p = [local_config.base_port]
    containers = client.containers()
    for con in containers:
        if 'Ports' in con and len(con['Ports']) > 0:
            for port in con['Ports']:
                if 'PublicPort' in port:
                    p.append(int(port['PublicPort']))
    return p

def get_max_port():
    """ return highest port number that is NOT in use
        WARNING: port is integer
    """
    p = [local_config.base_port]

    containers = client.containers()
    for con in containers:
        if 'Ports' in con and len(con['Ports']) > 0:
            for port in con['Ports']:
                if 'PublicPort' in port:
                    p.append(int(port['PublicPort']))
    return (max(p) + 1)


def list_all_containers():
    """list all Docker containers
    returns list of dict
    """
    containers = client.containers(all=True, filters={'label': 'DBaaS=true'})
    return containers


def inspect_con(con_name=None, id=None):
    """docker inspect for <con_name>"""
    if con_name:
        target = con_name
    elif id:
        target = id
    else:
        print('Error: inspect: Must provide container name or Id')
        return {}
    try:
        insp = client.inspect_container(target)
    except docker.errors.NotFound:
        raise Notfound('Container %s not found' % con_name)
    return insp


def container_exists(dbname):
    """ return True/False if <dbname> is a container. docker ps -a
    """
    try:
        insp = client.inspect_container(dbname)
    except docker.errors.NotFound as e:
        return False
    return True


def restart(con_id):
    '''restart container '''
    client.restart(con_id)

def restart_con(dbname, dbuser, dbuserpass, username, admin_log=True):
    """ restart container
       - determin which container type
       - check authentication with db
       - restart docker container
    """
    state_info = admin_db.get_container_state(dbname)
    data = admin_db.get_container_data('', state_info.c_id)
    dbengine = data['Info']['dbengine']
    port = data['Info']['Port']

    auth = False
    if dbengine == 'Postgres':
        auth = postgres_util.auth_check(dbuser, dbuserpass, port)
    elif dbengine == 'MongoDB':
        auth = mongodb_util.auth_mongodb(dbuser, dbuserpass, port)
    elif dbengine == 'MariaDB':
        auth = mariadb_util.auth_mariadb(dbuser, dbuserpass, port)
    elif dbengine == 'Neo4j':
        auth = neo4j_util.auth_check(dbuser, dbuserpass, port)
    else:
        return "Error: container type not found"
    if auth:
        try:
            client.restart(dbname)
            result = "%s successfully restarted" % dbname
        except Exception, e:
            result = "An error occured: %s" % e
        if admin_log:
            state_info = admin_db.get_container_state(dbname)
            message = 'Restarted by %s' % username
            admin_db.add_container_log(state_info.c_id, dbname, message,
                                       description='')
    else:
        result = "Authentication failed; You must be super user to restart"
    return result


def stop_remove(dbname):
    """stop and remove docker container
    this should not be accessed directly, but from kill_con()
    Kill_con will cleanup the admin_db 
    """
    try:
        client.stop(dbname)
        client.remove_container(dbname)
        return True
    except Exception, e:
        print("Error: stop_remove: %s" % e )
        return False


def admin_kill(dbname, username):
    """ Stop and remove container without using authtication.
    Called from the admin command console Only. Clean up 
    admin_db. Implemented becuase I forget passwords.
    """
    if stop_remove(dbname):
        result = "Container %s successfully deleted " % dbname
        result += "from admin console by %s" % username
        send_mail("DBaaS: container removed", result)
    state_info = admin_db.get_container_state(dbname)
    if state_info:
        admin_db.delete_container_state(state_info.c_id)
        description = 'deleted %s by user %s' % (dbname, username)
        admin_db.add_container_log(state_info.c_id, dbname, 'deleted', description)


def kill_con(dbname, dbuser, dbuserpass, username):
    """ stop and remove container
    """
    #  get state info (running container)
    state_info = admin_db.get_container_state(dbname)
    data = admin_db.get_container_data('', state_info.c_id)
    dbengine = data['Info']['dbengine']
    port = data['Info']['Port']

    print('DEBUG: kill_con: con: %s user: %s pass: %s port: %s' % (
        dbname, dbuser, dbuserpass, port))
    auth = False
    if dbengine == 'Postgres':
        auth = postgres_util.auth_check(dbuser, dbuserpass, port)
    elif dbengine == 'MongoDB':
        auth = mongodb_util.auth_mongodb(dbuser, dbuserpass, port)
    elif dbengine == 'MariaDB':
        auth = mariadb_util.auth_mariadb(dbuser, dbuserpass, port)
    elif dbengine == 'Neo4j':
        auth = True
    else:
        return "Error: Container not found"

    if auth:
        print("auth is true; deleting: %s" % dbname)
        admin_kill(dbname, username)
        result = "Container %s successfully deleted. " % dbname
        result += "Container type: %s" % dbengine
    else:
        result = "Authentication failed; You must be super user to remove"
    return result


def make_dirs(con_name, volumes):
    """ Create data and backup directories for new container
    """
    for dir in volumes:
        if not dir[0]:
            continue
        path = dir[0] + '/' + con_name + dir[1]
        print("DEBUG: makedir(%s)" % path)
        try:
            os.makedirs(path)
            os.chmod(path, 0o777)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                print("Error creating directory: %s errno: %s" % (path, exc))

def create_backupdir(con_name):
    """ Create subdirectory within backup volume for backup 
        used by all db containers.
        return directory name, backup_id used for backup_log
    """
    t = time.localtime()
    backup_id = '%s%02d%02d-%02d:%02d:%02d' % (t[0], t[1], t[2],
                                               t[3], t[4], t[5])
    dirname = "/%s_" % con_name
    dirname += "%s-%02d-%02d_" % (t[0], t[1], t[2]) # Year, Mon, Day
    dirname += "%02d-%02d-%02d" % (t[3], t[4], t[5]) # Hour Min Sec
    # create dirctory to hold all files for backup
    path = local_config.var.backup_vol + '/' + con_name + '/' + dirname
    os.makedirs(path)
    return dirname, backup_id

def build_arguments(params, labels, volumes, bindings):
    """build volumes and bindings for create_container"""
    con_name = params['dbname']
    dbtype = params['dbtype']
    db_vol = params['db_vol']
    for dir in local_config.info[dbtype]['volumes']:
        volumes.append(dir[2])
        if not dir[0]:
            vol = dir[1]
        else:
            if dir[0] == 'DBVOL':
                vol = db_vol + '/' + con_name + dir[1]
            else:
                vol = dir[0] + '/' + con_name + dir[1]
        bindings[vol] = {}
        bindings[vol] = {'bind': dir[2], 'mode': 'rw'}
    labels["DBaaS"] = "true"
    labels["dbengine"] = params['dbtype']
    labels["SUPPORT"] = params['support']
    labels["OWNER"] = params['owner']
    labels["DB_NAME"] = params['dbname']
    labels["DB_USER"] = params['dbuser']
    labels["DESCRIPTION"] = params['description']
    labels["CONTACT"] = params['contact']
    labels["LIFE"] = params['life']
    labels["BACKUP_FREQ"] = params['backup_freq']
    labels["BACKUP_WINDOW"] = params['backup_window']
    labels["MAINTAIN"] = params['maintain']
    labels["PHI"] = params['phi']
    if 'longpass' in params:
        labels["LONGPASS"] = params['longpass']


def create_con(params, env, args=None):
    """Create new container
       <params> dict of specific parameters for a given container:
       dbname, username, userpass, lables and environment
       args: Arguments to "run" command. (Example: run mongo --auth)
       params['port_bindings'] is a dict of ports that need to be mapped.
             {'3306': ('140.107.117.18', '30020')}
    """
    dbtype = params['dbtype']
    con_name = params['dbname']
    if not args:
        args = ''
    volumes = []
    bindings = {}
    con_labels = {}
    build_arguments(params, con_labels, volumes, bindings)
    env['TZ'] = local_config.var.TZ
    msg = json.dumps(env, indent=4)
    print("DEBUG: container_util; create_con: env=%s" % msg)
    msg = json.dumps(params, indent=4)
    print("DEBUG: container_util; params: %s" % msg)
    print("DEBUG: container_util; create_con: ports=%s" % params['port_bindings'])
    host_conf = client.create_host_config(mem_limit=0,
                                       restart_policy={'Name': 'on-failure'},
                                       port_bindings=params['port_bindings'],
                                       binds=bindings
                                       )
    print("con_labels: ", con_labels)
    print("volumes: (%s)" % type(volumes))
    print("volumes: ", volumes)
    print("disk bind: ", bindings)
    con = client.create_container(image=params['image'],
                               name=con_name,
                               detach=True,
                               command=args,
                               environment=env,
                               labels=con_labels,
                               ports=local_config.info[dbtype]['pub_ports'],
                               volumes=volumes,
                               host_config=host_conf,
                               )
    msg = json.dumps(con, indent=4)
    print("DEBUG: container_util; create_con: result=%s" % msg)
    client.start(con['Id'])

    # Admin_db - add container, add state, log creation
    if con_name == 'mydb_admin':
         return -1, con 
    inspect = inspect_con(con['Id'])
    c_id = admin_db.add_container(inspect, params)
    state_info = admin_db.get_container_state(con_name)
    description = 'created %s by user %s' % (con_name, params['username'])
    admin_db.add_container_log(c_id, con_name, 'created', description)
    return c_id, con
