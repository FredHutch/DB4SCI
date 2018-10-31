#!/usr/bin/python
import os
import time
import postgres_util
import container_util
import admin_db
from send_mail import send_mail
import local_config


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
    print('wait for container to start')
    time.sleep(12)
    admin_db.init_db()
    inspect = container_util.inspect_con(params['con']['Id'])
    c_id = admin_db.add_container(inspect, params)
    state_info = admin_db.get_container_state(con_name)
    description = 'created %s by user %s' % (con_name, params['username'])
    admin_db.add_container_log(c_id, con_name, 'created', description)
    

def setup_data():
    """ create parameters for admin database
    """
    mydb_root = os.environ.get('MYDB_ROOT')
    print('MYDB_ROOT: %s' % mydb_root)
    dbtype = 'Postgres'
    params = {'dbname': 'mydb_admin',
              'dbtype': dbtype,
              'dbengine': dbtype,
              'port': local_config.var.mydb_admin_port,
              'dbuser': local_config.var.accounts['admindb']['admin'],
              'dbuserpass': local_config.var.accounts['admindb']['admin_pass'],
              'db_vol': mydb_root + 'dbs_data/',
              'bak_vol': mydb_root + 'db_backups/',
              'support': 'Basic',
              'owner': local_config.var.accounts['admindb']['owner'],
              'description': 'Test the Dev',
              'contact': local_config.var.accounts['admindb']['contact'],
              'life': 'long',
              'backup_type': 'User',
              'backup_freq': 'Daily',
              'backup_life': '6',
              'backup_window': 'any',
              'phi': 'No',
              'pitr': 'n',
              'maintain': 'standard',
              'username': local_config.var.accounts['admindb']['admin'],
              'image': local_config.info[dbtype]['images'][0][1],
              }
    return params
