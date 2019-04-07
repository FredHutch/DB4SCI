#!/usr/bin/python
import os
import sys
import time
import json
import container_util
import admin_db
from send_mail import send_mail
import pymysql
from config import Config
import neo4j.v1 as neo4j
from neo4j.v1 import GraphDatabase, basic_auth


def auth_check(dbuser, dbpass, port):
    """
    Ckeck if <dbuser> account is authorized user.
    :type dbuser: basestring
    :type dbpass: basestring
    :type port: basestring
    :returns  True/False
    """
    url = 'bolt://' + Config.container_ip + ':' + str(port)
    try:
        driver = GraphDatabase.driver(url, auth=basic_auth(dbuser, dbpass))
    except:
        e = sys.exc_info()[0]
        print('DEBUG: %s' % e)
        return False
    return True


def reset_neo4j_password(port):
    """This routine only works once on a new instance of neo4j.
    Login with temp pass word of "changeme" and reset neo4j pass word
    """
    url = 'bolt://' + Config.container_ip + ':' + str(port)
    password = Config.accounts['Neo4j']['admin_pass']

    try:
        driver = GraphDatabase.driver(url, auth=("neo4j", "changeme"))
    except:
        return False
    session = driver.session()
    query = 'CALL dbms.changePassword("%s")' % password
    try:
        status = session.run(query)
        # what to do with status? its and neo4j object
    except:
        print('Error: neo4j reset_neo4j_password: ')
        return False
    return True


def create_account(dbuser, dbuserpass, port):
    """Create Neo4j accounts
    specified in the configure file. Then add the user account.
    """
    url = 'bolt://' + Config.container_ip + ':' + str(port)
    password = Config.accounts['Neo4j']['admin_pass']

    try:
        driver = GraphDatabase.driver(url, auth=("neo4j", password))
    except:
        return False
    session = driver.session()

    query = 'CALL dbms.security.createUser("%s", "%s", false)' % (
                                                         dbuser, dbuserpass)
    try:
        status = session.run(query)
    except:
        print('Error: neo4j create_account createUser: %s' % status)
        return False
    return True


def create(params):
    """
    Create Neo4j Docker instance
    :param params: dict
    :return: Help message for end user
    """
    con_name = params['dbname']
    config_dat = Config.info[params['dbtype']]
    volumes = config_dat['volumes']
    for vol in volumes:
        if vol[0] == 'DBVOL': vol[0] = params['db_vol']
        if vol[0] == 'BAKVOL': vol[0] = Config.backup_vol
    if container_util.container_exists(con_name):
        return "Container name %s already in use" % con_name
    used_ports = container_util.get_ports()
    # find two consecutive ports that are not in usebolt_port
    for port in range(Config.base_port, max(used_ports) + 2):
        if port not in used_ports and (
           (port + 1) not in used_ports):
            break
    Ports = {}
    for p in config_dat['pub_ports']:
        Ports[int(p)] = (Config.container_ip, port)
        port += 1
    params['port_bindings'] = Ports
    bolt_port = params['port'] = Ports[7687][1]
    print("Ports: ", Ports)
    env = {'NEO4J_dbms_memory_pagecache_size': '4G',
           'NEO4J_AUTH': 'neo4j/changeme',
           'DB_USER': params['dbuser']}

    # create container
    container_util.make_dirs(con_name, volumes)
    command = config_dat['command']
    (c_id, con) = container_util.create_con(params, env, args=command)
    print('waiting for container to startup...')
    time.sleep(5)

    status = reset_neo4j_password(params['port'])
    if status:
        stat2 = create_account(params['dbuser'], params['dbuserpass'],
                               params['port'])
    badness = 0
    while status is not True and badness < 6:
        print('create_account failed: %d' % badness)
        time.sleep(3)
        status = reset_neo4j_password(params['port'])
        if status:
            stat2 = create_account(params['dbuser'],
                                   params['dbuserpass'],
                                   params['port'])
        badness += 1
    if status is not True:
        print('DEBUG very bad')
        return "Failed: neo4j unable to create accounts"
    https_port = Ports[7473][1]
    res = "Your neo4j container %s " % con_name
    res += "has been created.\n\n"
    res += "neo4j HTTPS interface: %d\n" % https_port
    res += "neo4j Bolt interface: %d\n" % bolt_port
    res += '\n'
    res += 'Web access: https://%s:%d' % (Config.container_host, https_port)
    res += '\n\n'
    res += 'Note: Web interface will display the default Bolt port of 7687. '
    res += 'Change the Bolt port number from 7687 to %s ' % bolt_port
    res += 'before loginging in.\n\n'
    res += 'bolt://%s:%d' % (Config.FQDN_host, bolt_port)
    msg = 'Neo4j created: %s\n' % params['dbname']
    msg += 'Created by: %s <%s>\n' % (params['owner'], params['contact'])
    send_mail("DB4SCI: created neo4j", msg)
    return res


def backup(params):
    """ neo4j - backup
    backup is performed by copying contents of the graph.db directory 
    to the backup volume.
    source: /data/databases/graph.db
    """
    neo4jDB = '/data/databases/graph.db'
    con_name = params['dbname']
    (c_id, dbengine) = admin_db.get_container_type(con_name)
    (backupdir, backup_id) = container_util.create_backupdir(con_name)
    if 'backup_type' in params:
        backup_type = params['backup_type']
    else:
        backup_type = 'NA'
    remote_dumppath = Config.info['Neo4j']['backupdir'] + backupdir
    local_dumppath = Config.backup_voll + '/' + con_name + backupdir
    bucket = os.environ.get('AWS_BUCKET')
    url = bucket + '/' + con_name + backupdir 
    command = "/bin/cp -rp %s %s" % (neo4jDB, remote_dumppath)
    print("DEBUG: neo4j backup command: %s" % command)
    admin_db.backup_log(c_id, con_name, 'start', backup_id, backup_type, url='',
                        command=command, err_msg='')
    error = container_util.exec_command(con_name, command)
    if len(error) > 0:
        message += "\nError:\n" + error
    else:
        root = local_dumppath + '/graph.db'
        message = ("File list:\n%12s %s\n" % ('Bytes', 'File Name'))
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            size = os.stat(path).st_size
            message += ("%12d %s\n" % (size, name))
    admin_db.backup_log(c_id, con_name, 'end', backup_id, backup_type,
                        url, command, error)
    return command, message
