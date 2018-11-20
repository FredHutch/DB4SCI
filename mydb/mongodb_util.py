#!/usr/bin/python
import os
import sys
import errno
import time
import json
from flask import Flask, session
import pymongo
from pymongo import MongoClient
import container_util
import admin_db
from send_mail import send_mail
from config import Config


def auth_mongodb(dbuser, dbpass, port):
    client = MongoClient(Config.container_host + ':' + str(port))
    try:
        status = client.admin.authenticate(dbuser, dbpass)
    except (pymongo.errors.ServerSelectionTimeoutError,
            pymongo.errors.OperationFailure) as e:
        return False
    client.close()
    return True


def mongodb_create_account(params):
    """ Create admin roles and user account
    """
    root = Config.accounts[params['dbtype']]['admin']
    password = Config.accounts[params['dbtype']]['admin_pass']
    print("DEBUG: create root account: %s:%s" % (root, password))
    client = MongoClient(Config.container_host + ':' + str(params['port']))
    client.admin.add_user(root, password, roles=[{'role': 'root',
                                                  'db': 'admin'}])
    client.admin.add_user(params['dbuser'], params['dbuserpass'],
                          roles=[{'role': 'root', 'db': 'admin'}])
    client.close()
    return 'ok'


def create_mongodb(params):
    dbtype = params['dbtype']
    con_name = params['dbname']
    config_dat = Config.info[dbtype]
    volumes = config_dat['volumes']
    for vol in volumes:
        if vol[0] == 'DBVOL': vol[0] = params['db_vol']
        if vol[0] == 'BAKVOL': vol[0] = Config.backup_vol
    if container_util.container_exists(con_name):
        return "Container name %s already in use" % (con_name)
    port = container_util.get_max_port()
    params['port'] = port
    Ports = {config_dat['pub_ports'][0]: (Config.container_ip, port)}
    params['port_bindings'] = Ports
    env = {'DB_USER': params['dbuser']}

    # create container without Auth enabled
    container_util.make_dirs(con_name, volumes)
    (c_id, con) = container_util.create_con(params, env, config_dat['command'])
    print("DEBUG: noauth MongoDB created. Sleeping while it starts.\n")
    time.sleep(4)

    mongodb_create_account(params)

    print("DEBUG: stop and remove container")
    root = Config.accounts[params['dbtype']]['admin']
    password = Config.accounts[params['dbtype']]['admin_pass']
    result = container_util.kill_con(params['dbname'],
                                     root, password, params['username'])
    print("DEBUG: mongodb_util kill: %s" % result)
    admin_db.delete_container(c_id)  # we don't duplicate container data
    print('Sleeping a bit before recreating mongo')
    time.sleep(4)

    print("DEBUG: Start with Auth")
    (c_id, con) = container_util.create_con(params, env, '--auth')
    print("DEBUG: MongoDB with --auth created: %s." % con['Id'])
    res = "Your MongoDB container has been created; %s\n\n" % con_name
    res += 'Mongo URI: "mongodb://%s:%s@%s:%s"' % (params['dbuser'],
                                                   params['dbuserpass'],
                                                   Config.container_host,
                                                   port)
    message = 'MongoDB created\n'
    message += res
    send_mail("MyDB: created MongoDB", message)
    return res


def backup_mongodb(dbname, type, tag=None):
    (backupdir, backup_id) = container_util.create_backupdir(dbname)
    (c_id, dbengine) = admin_db.get_container_type(dbname)
    bucket = os.environ.get('AWS_BUCKET')
    url = l = bucket + '/' + dbname + backupdir 
    cmd = 'mongodump --username %s ' % Config.accounts['MongoDB']['admin']
    cmd += '--password %s ' % Config.accounts['MongoDB']['admin_pass']
    cmd += '--out /var/backup' + backupdir  # OR --archive >filename
    admin_db.backup_log(c_id, dbname, 'start', backup_id, type, url='',
                        command=cmd, err_msg='')
    result = container_util.exec_command(dbname, cmd)
    admin_db.backup_log(c_id, dbname, 'end', backup_id, type, url, cmd, result)
    return cmd, result
