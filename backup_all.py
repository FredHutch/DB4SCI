#!/usr/bin/python
import subprocess
import sys
import json
import time
import datetime
import psycopg2
import logging
import logging.handlers
import argparse
import smtplib
import requests
from docker import Client
import mydb.admin_db as admin_db
import mydb.postgres_util as postgres
import mydb.mariadb_util as mariadb
import mydb.mongodb_util as mongodb
import mydb.neo4j_util as neo4j
from config import Config
from mydb.send_mail import send_mail

"""Database backup module for Postgres DBaaS.
   Run as a nightly backup of postgres instances for all containers.
   This module is called from cron or the command line.
   This is not part of the DBaas flask application
"""


def backup_container(con_name, weekly):
    """ backup container
    if container not in running state return error
    <weekly> boolean to force backup of weekly when not scheduled
    """
    error = ''
    state = admin_db.get_container_state(con_name)
    if state is None:
        return '%s: container not found' % con_name
    if state.state != 'running':
        return '%s: container Not Running' % con_name
    data = admin_db.get_container_data('', state.c_id)
    info = data['Info']
    backup_type = info['BACKUP_FREQ']
    info['backup_type'] = backup_type
    info['c_id'] = state.c_id
    info['username'] = 'backup_all'
    backup_id = datetime.datetime.now().strftime("%Y%m%d.%H%M%S")
    t = time.localtime()
    if weekly and backup_type == 'Weekly':
        pass
    elif backup_type == 'Daily' or (
       backup_type == 'Weekly' and t[6] == 5):
        pass
    else:
        return '%s does not require backups' % info['Name']
    info['dbname'] = info['Name']
    info['username'] = 'cron'
    if 'dbengine' in info:
        start = time.time()
        created = datetime.datetime.now()
        logging.info('%4d %-30s %-10s %-s %s' % (state.c_id, info['dbname'],
                                                 info['dbengine'],
                                                 info['BACKUP_FREQ'],
                                                 str(info['Port'])))
        if info['dbengine'] == 'MongoDB':
            (command, err_msg) = mongodb.backup_mongodb(info['dbname'],
                                                        backup_type)
        elif info['dbengine'] == 'MariaDB':
            (command, err_msg) = mariadb.backup_mariadb(info)
        elif info['dbengine'] == 'Postgres':
            (command, err_msg) = postgres.backup(info)
        elif info['dbengine'] == 'Neo4j':
            (command, err_msg) = neo4j.backup(info)
        error = err_msg
        end = time.time()
        msg = '<%s> id=%d Elapsed: %s Msg: <%s>'
        print(msg % (con_name, state.c_id, str(round(end-start)), err_msg))
    else:
        logging.error("Error: %s add dbengine to info" % info['Name'])
    return error


def backup_all(weekly):
    """perform database backups for all containers
    if weekly flag is true:
        backup containers with Weekly backups defined
    """
    error = ''
    logging.info("DBaaS nightly Backups begining")
    t = time.localtime()
    ts = "%s-%02d-%02d_%02d-%02d-%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    containers = admin_db.list_active_containers()

    for (c_id, con_name) in containers:
        error = backup_container(con_name, weekly)
        if len(error) > 0:
            logging.error(error)

    send_mail("MyDB: backup_all db",
              "Backup_all has completed the database backups",
              config.backup_admin_mail)


def offsite_backup():
    """Sends the DB Dumps to an S3 bucket"""
    msg = "%s --only-show-errors  s3 sync %s %s --sse"
    cmd = msg % (config.aws, config.backupvol, config.bucket)
    logging.info("Sending backups to the Cloud. cmd: (%s)" % cmd)
    backup_id = datetime.datetime.now().strftime("%Y%m%d")
    admin_db.backup_log(0, 'offsite', 'start', backup_id, 'AWS S3',
                        config.bucket, cmd, "")
    print("AWS backup command:", cmd)
    start = time.time()
    out = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    processed, _ = out.communicate()
    end = time.time()
    if len(processed) > 0:
        msg = "Error: problem sending backups to the cloud: %s"
        logging.error(msg, processed)
        send_mail("PostgresDB: AWS backup error",
                  "AWS syn backup errors ocurred. Error: %s" % processed,
                  config.backup_admin_mail)
    else:
        duration = ('duration: %s seconds' % str(round(end - start)))
        admin_db.backup_log(0, 'offsite', 'end', backup_id, 'AWS S3',
                            config.bucket, duration, "")
        logging.info("AWS backup complete. %s", duration)


if __name__ == "__main__":
    FORMAT = "%(asctime)s %(module)s:%(levelname)s: %(message)s"
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.SysLogHandler(address=('loghost', 514))
    formatstr = 'mydb.backup_all: %(levelname)s: %(message)s'
    formatter = logging.Formatter(formatstr)
    handler.setFormatter(formatter)
    log.addHandler(handler)

    logging.basicConfig(level=logging.DEBUG, format=FORMAT,
                        filename=config.backup_log)
    msg = 'perform database backups for all containers'
    parser = argparse.ArgumentParser(description=msg)

    parser.add_argument('--weekly', dest='weekly', required=False,
                        action='store_true',
                        help='Only perform weekly backups')
    parser.add_argument('container', nargs='?')
    args = parser.parse_args()

    if args.container:
        backup_container(args.container, args.weekly)
    else:
        backup_all(args.weekly)
    offsite_backup()
    logging.info("mydb backups complete")
    send_mail("MyDB: backup_all complete",
              "backup_all has run",
              config.backup_admin_mail)
