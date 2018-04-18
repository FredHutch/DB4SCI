#!/usr/bin/python
import subprocess
import sys
import json
import time
import datetime
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
import mydb.neo4j_util as neo4j
import mydb.config as config
from mydb.send_mail import send_mail

"""Database backup module for Postgres DBaaS.
   Run as a nightly backup of postgres instances for all containers.
   This module is called from cron or the command line.
   This is not part of the DBaas flask application
"""


def backup_all():
    error = ''
    logging.info("DBaaS nightly Backups begining")
    t = time.localtime()
    ts = "%s-%02d-%02d_%02d-%02d-%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    containers = admin_db.list_containers()
    url = ''
    i = 1
    for (c_id, con_name) in containers:
        data = admin_db.get_container_data('', c_id)
        info = data['Info']
        backup_type = info['BACKUP_FREQ']
        info['backup_type'] = backup_type
        backup_id = datetime.datetime.now().strftime("%Y%m%d") + ".%02d" % i
        i += 1
        if backup_type == 'Daily' or (
           backup_type == 'Weekly' and t[6] == 5):
            pass
        else:
            logging.info('%s does not require backups' % info['Name'])
            continue
        info['dbname'] = info['Name']
        info['username'] = 'cron'
        if 'dbengine' in info:
            start = time.time()
            created = datetime.datetime.now()
            logging.info('%-30s %-10s %-s %s' % (info['dbname'],
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
            error += err_msg
            end = time.time()
            msg = '<%s> id=%d Elapsed: %s Msg: <%s>'
            print(msg % (con_name, c_id, str(round(end-start)), err_msg))
        else:
            logging.error("Error: %s add dbengine to info" % info['Name'])
    if len(error) > 0:
        logging.error(error)
    send_mail("MyDB: backup_all db",
              "Backup_all has completed the database backups",
              config.var.backup_admin_mail)


def offsite_backup():
    """Sends the DB Dumps to an S3 bucket"""
    msg = "%s --only-show-errors  s3 sync %s %s --sse"
    cmd = msg % (config.var.aws, config.var.backupvol, config.var.bucket)
    logging.info("Sending backups to the Cloud. cmd: (%s)" % cmd)
    backup_id = datetime.datetime.now().strftime("%Y%m%d")
    admin_db.backup_log(0, 'offsite', 'start', backup_id, 'AWS S3',
                        config.var.bucket, cmd, "")
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
                  config.var.backup_admin_mail)
    else:
        duration = ('duration: %s seconds' % str(round(end - start)))
        admin_db.backup_log(0, 'offsite', 'end', backup_id, 'AWS S3',
                            config.var.bucket, duration, "")
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
                        filename=config.var.backup_log)

    backup_all()
    offsite_backup()
    logging.info("mydb backups complete")
    send_mail("MyDB: backup_all complete",
              "backup_all has run",
              config.var.backup_admin_mail)
