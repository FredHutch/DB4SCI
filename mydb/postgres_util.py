#!/usr/bin/python
import os
import json
import time
import psycopg2
import string
import random
from shutil import copyfile
from send_mail import send_mail
import container_util
import admin_db
from config import Config

dbtype = 'Postgres'


def generate_password():
    chars = string.letters + string.digits + '!@#$%^&*'
    pwdSize = 20
    return ''.join((random.choice(chars)) for x in range(pwdSize))


def auth_check(dbuser, dbuserpass, port):
    """
    :type boolean
    port: int
    """
    connect = "dbname=postgres user=%s " % dbuser
    connect += "host=%s " % Config.container_host
    connect += "password=%s port=%s" % (dbuserpass, port)
    try:
        conn = psycopg2.connect(connect)
        cur = conn.cursor()
        cur.execute("SELECT rolsuper FROM pg_roles WHERE rolname ='" +
                    dbuser + "';")
        return cur.fetchall()[0][0]
    except Exception as e:
        print("Error: auth_check: %s" % e)
        return False


def create_accounts(params):
    """make changes to running Postgres docker container
    requires restart
    """
    connections = 50
    memnum = 1024

    st = "ALTER SYSTEM SET "
    settings = {'max_connections': connections,
                'shared_buffers': "'" + str(int(memnum/4)) + "MB'",
                'work_mem': "'" + str(int(memnum/connections)) + "MB'",
                'maintenance_work_mem': "'" + str(int(memnum/8)) + "MB'",
                'wal_buffers': "'8MB'",
                'effective_cache_size': "'" + str(int(memnum*.75)) + "MB'",
                'cpu_tuple_cost': .0003,
                'cpu_operator_cost': .0005,
                'fsync': 'off',
                'min_wal_size': "'1GB'",
                'max_wal_size': "'3GB'",
                'checkpoint_timeout': "'35min'",
                'max_parallel_workers_per_gather': 8,  #  Postgres > 9.6
                'checkpoint_completion_target': .9}
    msg = json.dumps(settings, indent=4)
    conn_string = "dbname=%s " % params['dbname']
    conn_string += "host=%s " % Config.container_host
    conn_string += "port=%s " % params['port']
    conn_string += "user=%s " % params['dbuser']
    conn_string += "password=%s" % params['dbuserpass']
    try:
        conn = psycopg2.connect(conn_string)
    except Exception as e:
        print("ERROR: postgres_util; create_accounts; connection: %s" % e)
        return 'connect error' 
    cur = conn.cursor()
    for key in settings:
        k = st+key+"="+str(settings[key])+";"
        conn.set_isolation_level(0)
        try:
            cur.execute(k)
        except Exception as e:
            print("ERROR: postgres_util; alterDB: %s" % e)
    svcaccount = 'svc_' + params['dbuser']
    accounts = [[Config.accounts[dbtype]['admin'],
                 Config.accounts[dbtype]['admin_pass']],
                [svcaccount, params['longpass']]
                ]
    for (user, passw) in accounts:
        try:
            cmd = "CREATE ROLE %s " % user
            cmd += "with SUPERUSER LOGIN PASSWORD '%s'" % passw
            cur.execute(cmd)
        except Exception as e:
            print("ERROR: postgres_util; create_accounts; create role: %s" % e)
    conn.commit()
    return 'ok'

def create(params):
    """Create Postgres Container"""
    con_name = params['dbname']
    config_dat = Config.info[params['dbtype']]
    volumes = config_dat['volumes']
    for vol in volumes:
        if vol[0] == 'DBVOL':
            vol[0] = params['db_vol']
    if container_util.container_exists(con_name):
        return "Container name %s already in use" % con_name
    # Ports is a dict of internal too external mappings
    if 'port' in params:
        port = params['port']
    else:
        port = container_util.get_max_port()
        params['port'] = port
    Ports = {config_dat['pub_ports'][0]: (Config.container_ip, port)}
    params['port_bindings'] = Ports
    params['longpass'] = generate_password()
    env = {'POSTGRES_DB': params['dbname'],
           'POSTGRES_USER': params['dbuser'],
           'POSTGRES_PASSWORD': params['dbuserpass']}

    # create container
    container_util.make_dirs(con_name, volumes)
    (c_id, con) = container_util.create_con(params, env, config_dat['command'])
    params['con'] = con
    print("DEBUG: %s created. ID=%s\n" % (dbtype, con['Id']))
    time.sleep(5)
    status = create_accounts(params)
    badness = 0
    while status == 'connect error' and badness < 6:
        time.sleep(3)
        badness += 1
        status = create_accounts(params)
    if status != 'ok':
        res = 'This is embarrassing. Your Postgres container; %s ' % params['dbname']
        res += 'has been created but I was unable to create your account.\n'
        res += 'This unfortunate incident will be reported to the MyDB admin staff.'
        send_mail("MyDB: Error creating account", res)
        return res
    # restart the container
    container_util.restart(con['Id'])
    res = "Your database server has been created. Use the following command "
    res += "to connect from the Linux command line.\n\n"
    res += "psql -h %s " % Config.container_host
    res += "-p %s -d %s " % (str(port), params['dbname'])
    res += "-U %s\n\n" % params['dbuser']
    res += "If you would like to connect to the database without entering a "
    res += "password, create a .pgpass file in your home directory.\n"
    res += "Set permissions to 600. Format is hostname:port:database:"
    res += "username:password.\n"
    res += "Cut/paste this line and place in your /home/user/.pgpass file.\n\n"
    res += Config.container_host + ":" + str(port) + ":" + params['dbname']
    res += ":" + params['dbuser'] + ":" + params['dbuserpass'] + "\n\n"
    res += "To use psql on the linux command line load the PostgreSQL"
    res += " module.\n"
    res += "module load PostgreSQL\n\n"

    message = 'Mydb created a new %s database called: %s\n' % (
       dbtype, params['dbname'])
    message += 'Created by: %s <%s>\n' % (params['owner'], params['contact'])
    send_mail("MyDB: created %s" % dbtype, message)
    return res


def backup(params, tag=None):
    """Backup all databases for a given Postgres container 
    pg_dump is run from the database container
    """
    error = ''
    dbtype = 'Postgres'
    con_name = params['dbname']
    (c_id, dbengine) = admin_db.get_container_type(con_name)
    (dirname, backup_id) = container_util.create_backupdir(con_name)
    state_info = admin_db.get_container_state(con_name)
    data = admin_db.get_container_data(con_name, state_info.c_id)
    if 'backup_type' in params:
        backup_type = params['backup_type']
    else:
        backup_type = data['Info']['BACKUP_FREQ']
    port = data['Info']['Port']
    db_vol = data['Info']['DBVOL']

    # Dump postgres account information
    localpath = Config.info[dbtype]['backupdir'] + dirname
    command = "pg_dumpall -g -w -U %s " % Config.accounts[dbtype]['admin']
    command += "-f %s/%s.sql" % (localpath, con_name)
    start = time.time()
    result = container_util.exec_command(con_name, command)
    if len(result) > 0:
        error += result
    # write start infor to backup log
    admin_db.backup_log(c_id, con_name, 'start', backup_id, backup_type, url='',
                        command=command, err_msg=result)

    # copy alter system commands
    dest = '/' + con_name + '/'
    src_file = db_vol + dest + 'postgresql.auto.conf'
    dest_file = Config.backup_voll + dest + dirname + '/postgresql.auto.conf'
    print('DEBUG: cp ' + src_file + ' ' + dest_file)
    copyfile(src_file, dest_file)

    # Get list of databases to be backed up
    connect = "dbname='postgres' user='%s' " % Config.accounts[dbtype]['admin']
    connect += "host=%s " % Config.container_host
    connect += "password='%s' " % Config.accounts[dbtype]['admin_pass']
    connect += "port=%s" % port
    message = '\nExecuted Postgres dump_all commands:\n'
    try:
        connection = psycopg2.connect(connect)
    except Exception as e:
        message = "Error: MyDB Postgres Backup; "
        message += "psycopg2 connect:  container: %s, " % con_name
        message += "message: %s," % e
        message += "connect string: %s" % connect
        print('ERROR: ' + message)
        return command, message
    cur = connection.cursor()
    select = "SELECT datname from pg_database where datname "
    select += "<> 'postgres' and datistemplate=false"
    cur.execute(select)
    dbs = cur.fetchall()
    # back up each database    
    for db in dbs:
        dbname = (db[0])
        if tag:
            dumpfile = '/' + con_name + "_" + dbname + "_" + tag + ".dump"
        else:
            dumpfile = '/' + con_name + "_" + dbname + ".dump"
        dumppath = localpath + dumpfile
        command = "pg_dump --dbname %s " % dbname 
        command += "--username %s  -F c -f %s" % (Config.accounts[dbtype]['admin'],
                                          dumppath)
        print("DEBUG: dump_now command: %s" % (command))
        result = container_util.exec_command(con_name, command)
        message += command
        message += '\nResult: ' + result + '\n'
    admin_db.add_container_log(state_info.c_id, con_name,
                               'GUI backup', 'user: ' + params['username'])
    bucket = os.environ.get('AWS_BUCKET')
    url = bucket + '/' + con_name + dirname 
    admin_db.backup_log(c_id, con_name, 'end', backup_id, backup_type, url=url,
                        command=command, err_msg=message)
    return command, message


def showall(params):
    """Execute Postgres SHOW ALL command """
    try:
        conn_string = "dbname=%s " % params['dbname']
        conn_string += "host=%s " % Config.container_host
        conn_string += "port=%d " % params['port']
        conn_string += "user=%s " % params['dbuser']
        conn_string += "password=%s" % params['dbuserpass']
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()
    except Exception as e:
        print("ERROR: postgres_util; showall: %s" % e)
        return
    cur.execute("SHOW ALL")
    rows = cur.fetchall()
    for row in rows:
        print(row[0], row[1])
