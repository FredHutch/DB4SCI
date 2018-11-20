#!/usr/bin/python
import os
import time
import postgres_util
import container_util
import admin_db
from send_mail import send_mail
from config import Config


"""
import mydb_setup
mydb_setup.mydb_setup()
"""

def mydb_setup():
    """Create mydb_admin database if it does not exist.
    DBAAS depends on mydb_admin database.
    """
    if container_util.container_exists('mydb_admin'):
        print('MyDB Administrative DB is running.\nStarting DBAAS')
        return
    print('Create Administrative DB')
    params = setup_data()
    dbtype = params['dbtype']
    con_name = params['dbname']
    result = postgres_util.create(params)
    # wait for container to startup
    print('Container Id: %s' % params['con']['Id'] )
    print('Waiting for mydb_admin to start')
    time.sleep(5)
    badness = 0
    status = False
    while (not status) and (badness < 6):
        badness += 1
        status = postgres_util.auth_check(params['dbuser'], 
                                          params['dbuserpass'], 
                                          params['port'])
        print('mydb_admin setup status: %s count: %d' % (status, badness))
        time.sleep(3)
    if not status:
        print('mydb_admin restart error. Could not setup db')
        return
    print('Setup mydb_admin tables')
    admin_db.init_db()
    inspect = container_util.inspect_con(params['con']['Id'])
    c_id = admin_db.add_container(inspect, params)
    state_info = admin_db.get_container_state(con_name)
    description = 'created %s by user %s' % (con_name, params['username'])
    admin_db.add_container_log(c_id, con_name, 'created', description)
    

def setup_data():
    """ create parameters for admin database
    """
    dbtype = 'Postgres'
    params = {'dbname': 'mydb_admin',
              'dbtype': dbtype,
              'dbengine': dbtype,
              'port': Config.admin_port,
              'dbuser': Config.accounts['admindb']['admin'],
              'dbuserpass': Config.accounts['admindb']['admin_pass'],
              'db_vol': "/opt/DB4SCI/admin_db/data",
              'bak_vol': "/opt/DB4SCI/admin_db/backup",
              'support': 'Basic',
              'owner': Config.accounts['admindb']['owner'],
              'description': 'Test the Dev',
              'contact': Config.accounts['admindb']['contact'],
              'life': 'long',
              'backup_type': 'User',
              'backup_freq': 'Daily',
              'backup_life': '6',
              'backup_window': 'any',
              'phi': 'No',
              'pitr': 'n',
              'maintain': 'standard',
              'username': Config.accounts['admindb']['admin'],
              'image': Config.info[dbtype]['images'][0][1],
              }
    return params
