#!/usr/bin/python
import os
import sys
import json
import time
import psycopg2
import logging
import logging.handlers
import smtplib
import requests
from docker import Client
import mydb.admin_db as admin_db
import mydb.postgres_util as postgres
import mydb.mariadb_util as mariadb
import mydb.mongodb_util as mongodb
import mydb.container_util as container_util
import mydb.config as config

"""Verify that containers are in running state.

  get list of containers from docker
  get list of containers from admin_db
  --> both lists should match <--

export DOCKER_CLIENT_TIMEOUT=120
"""


def check_directories(dirs, path, admin_list):
    for dir in dirs:
       if dir not in admin_list:
           print('container volume with no container: %s/%s' % (path,dir))


def check_storage(admin_list):
    db_dirs = os.listdir(config.var.dbvol)
    check_directories(db_dirs, config.var.dbvol, admin_list)
    backup_dirs = os.listdir(config.var.backupvol)
    check_directories(backup_dirs, config.var.backupvol, admin_list)


def watch_dog():
    dbtype = 'Postgres'

    logging.info("Watchdog begining")
    t = time.localtime()
    ts = "%s-%02d-%02d_%02d-%02d-%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    cli = Client(base_url=config.var.base_url)
    docker_containers = cli.containers()
    admin_list = admin_db.list_containers()
    inspect = {}
    docker_list = []
    for con in docker_containers:
        name = con['Names'][0][1:]
        docker_list.append(name)
        inspect[name] = 'running' 

    containers = []
    for (c_id, con_name) in admin_list:
        containers.append(con_name)
        data = admin_db.get_container_data('', c_id)
        info= data['Info']
        dbname = info['Name']
        info['username'] = 'cron'
        if con_name in docker_list:
            result = container_util.exec_command(dbname, 'uptime')
        else:
            print('%s is listed as running but is not!' % con_name)
            continue
        if 'load average' not in result:
            print('(%d) %s is not running' % (c_id, dbname))
            continue
        if con_name in inspect:
            inspect[con_name] = 'found'
        print("%-30s %-10s %-35s %s" % (info['Name'], info['dbengine'], info['Image'], info['BACKUP_FREQ']))
    for con in inspect:
        if inspect[con] == 'running':
            print('%s is running but not in admin' % con)
    return containers

if __name__ == "__main__":

    container_list = watch_dog()
    check_storage(container_list)
