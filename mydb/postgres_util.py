import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg
from jinja2 import Template

from mydb import migrate_db

from . import (
    admin_db,
    aws_util,
    mydb_actions,
    mydb_config,
    swarm_util,
    touched,
    backup_util,
)
from .send_mail import send_mail

dbengine = "Postgres"


def pg_connection_string(user, password, port):
    """Create a PostgreSQL connection string to use with psycopg.connect()"""
    return " ".join(
        [
            f"host={mydb_config.FQDN_host}",
            f"port={port}",
            "dbname=postgres",
            f"user={user}",
            f"password={password}",
        ]
    )


def auth_check(dbuser, dbuserpass, port):
    """Connect to Postgres with users credentinals to
    validate that they have access
    """
    connect = pg_connection_string(dbuser, dbuserpass, port)
    try:
        conn = psycopg.connect(connect)
    except Exception as e:
        print(f"auth_check Error: {e}", file=sys.stderr)
        return False
    conn.close()
    return True


def create_init_script(params):
    """create PostgreSQL init script to create user account and default database

    PostgreSQL initialization scripts in /docker-entrypoint-initdb.d/ are executed
    automatically when the container starts for the first time (when data directory is empty).
    """

    sql_init_script = """-- Create Role
CREATE ROLE {{dbuser}} WITH LOGIN PASSWORD '{{dbuserpass}}';
ALTER USER {{dbuser}} WITH SUPERUSER;

-- Create Database
CREATE DATABASE "{{dbname}}";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE "{{dbname}}" TO {{dbuser}};

"""

    template = Template(sql_init_script)
    rendered_output = template.render(params)
    params["config_name"] = f"mydb_{params['Name']}_init.sql"
    target_path = "/docker-entrypoint-initdb.d/init.sql"
    return swarm_util.create_config(params, rendered_output, target_path)


def create_compose(params):
    """create docker compose file"""
    with open("mydb/compose_templates/postgresql.yml") as f:
        pg_template = f.read()
    template = Template(pg_template)
    rendered_ouput = template.render(params)
    composef = open(f"mydb/compose_scripts/{params['Name']}.yml", "w")
    composef.write(rendered_ouput)
    composef.close()


def pg_env(auth_meth=None) -> list:
    """create Postgres Env"""
    env = [
        f"POSTGRES_USER={mydb_config.accounts[dbengine]['admin']}",
        f"POSTGRES_PASSWORD={mydb_config.accounts[dbengine]['admin_pass']}",
        "POSTGRES_DB=postgres",
    ]
    if auth_meth == "md5":
        env.append("POSTGRES_INITDB_ARGS=--auth-host=md5")
    env.append(f"TZ={mydb_config.TZ}")
    return env


def build_params_postgres(info) -> dict:
    """Use the container metadata from version 1 of mydb to create a params dict
    This is only required for `migrate`.
    Args:
        params (dict): Service configuration parameters including image,
            dbname, service_user, env, volume_name, port, default_port,
            and labels.
    """
    params = {}
    dbengine = info["dbengine"]
    params["dbengine"] = info["dbengine"]
    params["image"] = mydb_config.info[dbengine]["images"][0][1]
    params["default_port"] = mydb_config.info[dbengine]["default_port"]
    params["service_user"] = mydb_config.info[dbengine]["service_user"]
    params["dbname"] = info["Name"]
    params["Name"] = info["Name"]
    if "POSTGRES_USER" in info:
        params["dbuser"] = info["POSTGRES_USER"]
    elif "DB_USER" in info:
        params["dbuser"] = info["DB_USER"]
    params["Port"] = info["Port"]
    # Environtment
    params["env"] = pg_env(auth_meth="md5")
    params["labels"] = {
        "Name": params["Name"],
        "DBaaS": "True",
        "backup_freq": info["BACKUP_FREQ"],
        "contact": info["CONTACT"],
        "username": params["dbuser"],
        "dbname": params["dbname"],
        "dbuser": params["dbuser"],
        "description": info["DESCRIPTION"],
        "owner": info["OWNER"],
        "touched": touched.create_date_string(),
    }
    return params


def migrate(info):
    """migrate postgres container
    Use meta data from v1 of mydb to create new docker swarm service
    """
    dbname = info["Name"]
    if swarm_util.service_exists(dbname):
        return f"Container name {dbname} already in use"
    volume_name = f"mydb_{dbname}"
    _, error = swarm_util.create_docker_volume(volume_name)
    if error:
        return r"Error creating docker volume {volume_name}. Error: {error}"
    params = build_params_postgres(info)
    params["service_name"] = f"mydb_{dbname}"
    params["volume_name"] = volume_name
    params['mapped_db_vol'] = "/var/lib/postgresql/data"
    S3_prefix = migrate_db.lastbackup_s3_prefix(dbname)
    # params["S3_prefix"] = S3_prefix
    config_ref = create_init_script(params)
    if config_ref is None:
        return "Error: creating Docker Config"
    # create_compose(params)
    service, error = swarm_util.start_service(params, config_ref)
    if service is None:
        return f"{error} {mydb_config.supportOrganization} has been notified"

    params["Start Mesg"] = f"Started! Service_id: {service.id}"
    params["service_id"] = service.id
    meta_data = json.dumps(params, indent=4)
    print(meta_data)
    time.sleep(4)  #  remove "start_service" waits till service is started
    result = pg_restore(params, params, S3_prefix)
    print(f"==== DEBUG: postgres_util.migrate: {dbname}\n{result}")
    return result


def create(params):
    """Create Postgres Container
    Called from mydb_views
    params is created from gerneral_form UI
    """
    data = json.dumps(params, indent=4)
    print(f"DEBUG: postgres_util.create: params before: {data}")
    params["service_name"] = f"mydb_{params['Name']}"
    params["volume_name"] = f"mydb_{params['Name']}"
    if swarm_util.service_exists(params["service_name"]):
        return f"Container name {params['service_name']} already in use"
    volume_id, error = swarm_util.create_docker_volume(params["volume_name"])
    if error:
        return f"Error creating docker volume {params['volume_name']}. Error: {error}"
    config_ref = create_init_script(params)
    if config_ref is None:
        return "Error: creating Docker Config"

    config_data = mydb_config.info[params["dbengine"]]
    params["mapped_db_vol"] = config_data["mapped_volume"]
    params["default_port"] = config_data["default_port"]
    params["service_user"] = config_data["service_user"]  # 'postgres'
    params["Port"] = admin_db.get_max_port()
    params["env"] = pg_env()
    params["labels"] = {}
    for label in mydb_config.mydb_v1_meta_data:
        params["labels"][label] = params[label]
    params["labels"]["touched"] = touched.create_date_string()
    service, error = swarm_util.start_service(params, config_ref)
    if service is None:
        return f"{error} {mydb_config.supportOrganization} has been notified"
    res = "Your database server has been created. Use the following command "
    res += "to connect from the Linux command line.\n\n"
    res += f"psql -h {mydb_config.FQDN_host} "
    res += f"-p {params['Port']} -d {params['dbname']} "
    res += f"-U {params['dbuser']} --password\n\n"
    res += "If you would like to connect to the database without entering a "
    res += "password, create a .pgpass file in your home directory.\n"
    res += (
        "Set permissions to 600. Format is hostname:port:database:username:password.\n"
    )
    res += "Cut/paste this line and place in your /home/user/.pgpass file.\n\n"
    res += f"{mydb_config.FQDN_host}:{params['Port']}:{params['dbname']}"
    res += f":{params['dbuser']}:PASSWORD\n\n"
    res += "To use psql on the linux command line load the PostgreSQL module.\n"
    res += "module load PostgreSQL\n\n"

    message = (
        f"Mydb created a new {dbengine} database called: {params['service_name']}\n"
    )
    message += f"Created by: {params['owner']} <{params['contact']}>\n"
    send_mail(f"MyDB: created {dbengine}", message, mydb_config.supportAdmin)
    return res


def backup(info, backup_type):
    """Backup all databases for a given Postgres container
    pg_dump commands are run locally and stream directly to S3
    type: str ['User', 'Admin']
    """
    Name = info["Name"]
    backup_id, prefix = aws_util.create_backup_prefix(Name)

    aws_bucket = mydb_config.AWS_BUCKET_NAME
    s3_url = f"{aws_bucket}{prefix}{Name}.sql"
   
    dump_command = ["pg_dumpall", "-g", "-w", "--lock-wait-timeout=8000",
                    "--host", mydb_config.FQDN_host, "--port", str(info['Port']),
                    "-U", mydb_config.accounts[dbengine]['admin']]
    env = {"PGPASSWORD": mydb_config.accounts[dbengine]['admin_pass']}

    # Log backup start
    admin_db.backup_log(
        info["cid"],
        Name,
        "start",
        backup_id,
        backup_type,
        url=s3_url,
        command=' '.join(dump_command),
        err_msg="",
    )

    message = f"\nExecuting Postgres backup to S3: {aws_bucket}\n"
    message += f"Executing Postgres dump_all globals command: pg_dumpall {' '.join(dump_command)}\n"
    message += f"     to: {prefix}{Name}_globals.sql\n"

    result, output = backup_util.backup_to_s3(dump_command, s3_url, env)

    if not result:
        message += f"Error: {output}"
        return message
    message += output

    # Get list of user databases to be backed up
    conn_string = pg_connection_string(
        mydb_config.accounts[dbengine]['admin'],
        mydb_config.accounts[dbengine]['admin_pass'],
        info['Port'],
    )
    try:
        connection = psycopg.connect(conn_string)
    except Exception as e:
        message = f"Error: MyDB Postgres Backup; "
        message += f"psycopg connect: container: {Name}, "
        message += f"message: {e}, "
        message += f"connect string: {conn_string}"
        print(f"ERROR: {message}")
        return message

    cur = connection.cursor()
    select = "SELECT datname FROM pg_database WHERE datname "
    select += "<> 'postgres' AND datistemplate=false"
    cur.execute(select)
    dbs = cur.fetchall()
    connection.close()


    message += f"\nBacking up {len(dbs)} database(s):\n"
    # Back up each database
    for db in dbs:
        dbname = db[0]
        s3_dump_url = f"{aws_bucket}{prefix}{Name}_{dbname}.dump"

        dump_command = [
            "pg_dump", "--dbname", dbname, "--lock-wait-timeout=5000", "--host",
            mydb_config.FQDN_host, "--port", str(info['Port']), "--username",
            mydb_config.accounts[dbengine]['admin']
        ]
        
        result, output = backup_util.backup_to_s3(dump_command, s3_dump_url, env)
        if not result:
            message += f"\nDatabase: {dbname}\n"
            message += f"Command: pg_dump {' '.join(dump_command)}\n"
            message += f"Error: {output}\n"
        else:
            message += "No errors in dump command."

        message += output

        print(f"DEBUG: backup command: {' '.join(dump_command)}")

    admin_db.add_container_log(
        info["cid"], Name, "GUI backup", f"user: {info.get('username', 'unknown')}"
    )

    url = f"{aws_bucket}{prefix}"
    admin_db.backup_log(
        info["cid"],
        Name,
        "end",
        backup_id,
        backup_type,
        url=url,
        command=' '.join(dump_command),
        err_msg=message,
    )
    print(f"DEBUG: message is:\n{message}")
    return message


def pg_audit(Info):
    """Comprehensive audit of a PostgreSQL instance

    Args:
        Info: Dictionary from database JSONB field containing container metadata
              Expected keys: Port, POSTGRES_USER, POSTGRES_PASSWORD

    Lists:
    1. All users/roles
    2. All databases (excluding template0, template1, postgres)
    3. All tables in each database
    4. Row count for each table

    Returns: formatted audit report string
    """
    report = []
    report.append("=" * 80)
    report.append("PostgreSQL Audit Report")
    report.append(f"Container: {Info.get('Name', 'unknown')}")
    report.append(f"Host: {mydb_config.FQDN_host}")
    report.append(f"Port: {Info['Port']}")
    report.append("=" * 80)
    report.append("")

    try:
        # Connect to postgres database to get system info
        conn_string = pg_connection_string(
            Info["username"],
            Info["dbuserpass"],
            Info["Port"],
        )
        conn = psycopg.connect(conn_string)
        cur = conn.cursor()

        # 1. List all users/roles
        report.append("USERS AND ROLES:")
        report.append("-" * 80)
        cur.execute("""
            SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
            FROM pg_roles
            ORDER BY rolname
        """)
        users = cur.fetchall()
        report.append(
            f"{'Role Name':<30} {'Superuser':<12} {'CreateDB':<10} {'CreateRole':<12} {'CanLogin':<10}"
        )
        report.append("-" * 80)
        for user in users:
            rolname, rolsuper, rolcreatedb, rolcreaterole, rolcanlogin = user
            report.append(
                f"{rolname:<30} {str(rolsuper):<12} {str(rolcreatedb):<10} {str(rolcreaterole):<12} {str(rolcanlogin):<10}"
            )
        report.append("")

        # 2. List all databases (exclude system databases)
        report.append("DATABASES:")
        report.append("-" * 80)
        cur.execute("""
            SELECT datname
            FROM pg_database
            WHERE datname NOT IN ('template0', 'template1', 'postgres')
            AND datistemplate = false
            ORDER BY datname
        """)
        databases = cur.fetchall()

        if not databases:
            report.append("No user databases found.")
            report.append("")
        else:
            for db_row in databases:
                dbname = db_row[0]
                report.append(f"\nDatabase: {dbname}")
                report.append("-" * 80)

                # Close current connection and connect to the specific database
                cur.close()
                conn.close()

                connect = pg_connection_string(
                    Info["username"],
                    Info["dbuserpass"],
                    Info["Port"],
                )
                connect = connect.replace("dbname=postgres", f"dbname={dbname}")
                db_conn = psycopg.connect(connect)
                db_cur = db_conn.cursor()

                # 3. List all tables in this database
                db_cur.execute("""
                    SELECT schemaname, tablename
                    FROM pg_tables
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schemaname, tablename
                """)
                tables = db_cur.fetchall()

                if not tables:
                    report.append(f"  No user tables found in database '{dbname}'")
                else:
                    report.append(f"{'Schema':<30} {'Table':<40} {'Row Count':<15}")
                    report.append("-" * 80)

                    # 4. Get row count for each table
                    for table_row in tables:
                        schemaname, tablename = table_row
                        try:
                            # Use count(*) to get row count
                            count_query = (
                                f'SELECT COUNT(*) FROM "{schemaname}"."{tablename}"'
                            )
                            db_cur.execute(count_query)
                            row_count = db_cur.fetchone()[0]
                            report.append(
                                f"{schemaname:<30} {tablename:<40} {row_count:<15,}"
                            )
                        except Exception as e:
                            report.append(
                                f"{schemaname:<30} {tablename:<40} {'ERROR: ' + str(e):<15}"
                            )

                db_cur.close()
                db_conn.close()

                # Reconnect to postgres database for next iteration
                if db_row != databases[-1]:  # If not the last database
                    conn = psycopg.connect(conn_string)
                    cur = conn.cursor()

        report.append("")
        report.append("=" * 80)
        report.append("Audit Complete")
        report.append("=" * 80)

    except Exception as e:
        error_msg = f"ERROR: pg_audit failed: {e}"
        print(error_msg)
        report.append("")
        report.append(error_msg)
        return "\n".join(report)

    return "\n".join(report)


def showall(params):
    """Execute Postgres SHOW ALL command"""
    connect = pg_connection_string(
        mydb_config.accounts[dbengine]["admin"],
        {mydb_config.accounts[dbengine]["admin_pass"]},
        params["Port"],
    )
    try:
        conn = psycopg.connect(connect)
        cur = conn.cursor()
    except Exception as e:
        print("ERROR: postgres_util; showall: %s" % e)
        return
    cur.execute("SHOW ALL")
    rows = cur.fetchall()
    for row in rows:
        print(row[0], row[1])
    cur.close()
    conn.close()


def pg_command(cmd, port, dbname):
    """Build PostgreSQL command with PGPASSWORD"""
    return "".join(
        [
            f"PGPASSWORD='{mydb_config.accounts[dbengine]['admin_pass']}' ",
            f"{cmd} -h {mydb_config.FQDN_host} ",
            f"-p {port} ",
            f"-d {dbname} ",
            f"-U {mydb_config.accounts[dbengine]['admin']}",
        ]
    )


def pg_restore(source, dest, S3_prefix):
    """Restore Postgres database from S3
    <source> and <dest> are container data structure: like `params`
    Postgres backup has a minimum of 3 files; control file, SQL file, dump file
    There may be multiple dump files for additional DB's
    require connection string to restore target

    Returns: all the stdout from the commands. If an error add the stderr, to
       the messages.  pg_dump restore never works without some kind of
       error messages/warnings.
    """
    # Source backup files
    backup_files = aws_util.list_s3_files(S3_prefix)
    print(f"backup file list: {backup_files}")
    psql_cmd = pg_command("psql", dest["Port"], dest["dbname"])
    pg_restore = pg_command("pg_restore", dest["Port"], dest["dbname"])

    # Run SQL command file
    result_msg = ""
    SQL_file = None
    for sql_file in backup_files:
        if ".sql" == sql_file[-4:]:
            SQL_file = sql_file
    if not SQL_file:
        return "Could not find a SQL file for PostgreSQL recovery. This is bad."
    restore_cmd = f"aws s3 cp {SQL_file} - | {psql_cmd}"
    print(f"DEBUG: restore SQL file: {restore_cmd}")
    base_sql = os.path.basename(SQL_file)
    if dest.get("SQL", "yes") != "no":
        try:
            result = subprocess.run(
                restore_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            if result.returncode != 0:
                error_msg = f"Error restoring SQL file: {result.stderr}"
                print(error_msg)
                return error_msg
            result_msg += (
                f"SQL file {base_sql} restored successfully\n{result.stdout}\n"
            )
        except subprocess.TimeoutExpired:
            return "SQL file restore timed out after 300 seconds.\nRestore incomplete"

        except Exception as e:
            return f"Unexpected error restoring SQL file: {e}"

    # Restore data from dump files
    for backup_file in backup_files:
        base_file = os.path.basename(backup_file)
        if ".dump" in backup_file[-5:]:
            restore_cmd = f"aws s3 cp {backup_file} - | {pg_restore}"
            print(f'DEBUG: restore dump file: "{restore_cmd}"')
            try:
                result = subprocess.run(
                    restore_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=1800,  # 20 minute timeout for larger dumps
                )
                if result.returncode != 0:
                    result_msg += f"Restoring: {base_file}\n"
                    result_msg += f"{result.stdout}\n"
                    result_msg += f"  Error: {result.stderr}\n"
                    print(result_msg)
                    print(f"cmd: {restore_cmd}")
                else:
                    print(f"Dump file restored successfully: {result.stdout}")
                    result_msg += f"Dump file {base_file} restored successfully\n{result.stdout}\n"
            except subprocess.TimeoutExpired:
                return f"Dump file {base_file} restore timed out after 1800 seconds"
            except Exception as e:
                result_msg += f"Error restoring dump file: {e}\n{result.stdout}\n"

    result_msg += "Database restored completed from S3."
    return result_msg


def recover_admin_db():
    """grab the backup of mydb_admin from S3 in '/prod' prefix.
    Once Version 2 goes live the version 1 DBs will need to be archived.
    So maybe change the prefix to /archive once V2 is live and copy the
    prod to /archive - Nov 2025

    This is where the migrate database is populated. 

    Currently this function times out when run in the web app context.
    """
    pg_restore = "".join(
        # TODO specify port? FIXME
        [
            f"PGPASSWORD='{mydb_config.accounts['admindb']['v1_admin_pass']}' ",
            "pg_restore -h admin_db ",
            "-d mydb_admin ",
            f"-U {mydb_config.accounts['admindb']['admin']}",
        ]
    )
    print(f"DEBUG: recover_admin_db: {pg_restore}")
    prefixs = aws_util.list_s3_prefixes("mydb_admin")
    if len(prefixs) == 0:
        return "No S3 backups found for mydb_admin."
    _, last_backup = prefixs[-1].split()
    aws_bucket = mydb_config.AWS_BUCKET_NAME
    print(f"DEBUG: recover_admin_db: {aws_bucket}/prod/mydb_admin/{last_backup}")
    S3_prefix = f"{aws_bucket}/prod/mydb_admin/{last_backup}"
    backup_files = aws_util.list_s3_files(S3_prefix)
    dump_file = None
    for backup_file in backup_files:
        if ".dump" in backup_file[-5:]:
            dump_file = backup_file
            break
    if dump_file is None:
        return f"Could not find dump file for mydb_admin. S3 correct? {S3_prefix}"
    base_file = os.path.basename(backup_file)
    restore_cmd = f"aws s3 cp {backup_file} - | {pg_restore}"
    result_msg = ""
    try:
        result = subprocess.run(
            restore_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=1200,  # 20 minute timeout for larger dumps
        )
        if result.returncode != 0:
            result_msg += f"Restoring: {base_file}\n"
            result_msg += f"{result.stdout}\n"
            result_msg += f"  Error: {result.stderr}\n"
        else:
            result_msg += (
                f"Dump file {base_file} restored successfully\n{result.stdout}\n"
            )
    except subprocess.TimeoutExpired:
        return f"Dump file {base_file} restore timed out after 1200 seconds"
    except Exception as e:
        result_msg += f"Error restoring dump file for mydb_admin: {e}\n{result.stdout}\n{result.stderr}"
    result_msg += "Database restored completed from S3."
    return result_msg


def setup_parser():
    parser = argparse.ArgumentParser(
        description="postgres_util CLI testing",
        usage="%(prog)s [options] module_name",
    )
    parser.add_argument(
        "--test-init", action="store_true", required=False, help="test SQL init script"
    )
    parser.add_argument(
        "--update-clone",
        required=False,
        action="store_true",
        dest="update",
        help="Used with --clone; The Cloned container will be the latest available DB version",
    )
    parser.add_argument(
        "--clone",
        action="store",
        dest="clone",
        help='Clone container, new container will have "_01" appended to name',
    )
    parser.add_argument(
        "--shm_size",
        action="store",
        dest="shm_size",
        help="Used with --clone option to set the shared mem size (/dev/shm), int or str, (e.g. 1G)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = setup_parser()
    if args.test_init:
        init_script({"dbuser": "jfdey", "dbuserpass": "jfdeytest", "dbname": "pgtest"})
