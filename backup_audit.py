#!/usr/bin/python
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
import mydb.config as config
from mydb.send_mail import send_mail

"""
audit MyDB backups. Check MyDB Admin backup logs.
verify that each data base in active state has been
backed up.
"""


def check_backup_logs(con_name, c_id, policy, verbose):
    """ query backup logs
    verify that backup started and ended
    verify that backup was run within policy (Daily or Weekly)
    """
    if policy == 'Daily':
        since = datetime.datetime.now() - datetime.timedelta(days=1)
    elif policy == 'Weekly':
        since = datetime.datetime.now() - datetime.timedelta(days=7)
    result = admin_db.backup_lastlog(c_id)
    start_id = end_id = None
    for row in result:
        if row.state == 'start':
            start_ts = row.ts
            start_id = row.backup_id
            if row.ts < since:
                msg = 'Warning: Last backup does not match Policy.'
                msg += 'Container: %s Policy: %s Time of last Backup: %s'
                print(msg % (con_name, policy, row.ts))
        if row.state == 'end':
            end_ts = row.ts
            end_id = row.backup_id
            url = row.url
    if start_id and end_id and start_id == end_id:   # this is good
        duration = end_ts - start_ts
        if verbose > 0:
            msg = '%-30s %6s duration: %s Start: %s Url:%s'
            print(msg % (con_name, policy, duration, start_ts, url))
    else:
        msg = 'Warning: Backup for <%s> started but did not finish! '
        msg += 'Start time: %s'
        print(msg % (con_name, start_ts))


def verify_container_backups(verbose):
    """ inspect the backup logs for every container that is running.
    get list of all "running" containers
    inspect backup logs based on backup policy for each container
    """
    check_list = []
    containers = admin_db.list_containers()
    for (c_id, con_name) in containers:
        data = admin_db.get_container_data('', c_id)
        if 'BACKUP_FREQ' in data['Info']:
            policy = data['Info']['BACKUP_FREQ']
        else:
            print('Extreme Badness: Backup policy not set for %s.' % con_name)
            continue
        if policy == 'Daily' or policy == 'Weekly':
            check_backup_logs(con_name, c_id, policy, verbose)
        else:
            if verbose > 0:
                print('%-30s %s' % (con_name, policy))

if __name__ == '__main__':
    verbose = 0
    if len(sys.argv) > 1 and sys.argv[1] == '--verbose':
        verbose = 1
    verify_container_backups(verbose)
