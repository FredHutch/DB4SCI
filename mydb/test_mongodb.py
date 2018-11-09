#!/usr/bin/env python
import os
import sys
import argparse
import time
import mongodb_util
import container_util
import admin_db
import volumes

from config import Config

def setup(dbtype, con_name):
    params = {'dbname': con_name,
              'dbuser': Config.accounts['test_user']['admin'],
              'dbuserpass': Config.accounts['test_user']['admin_pass'],
              'username': Config.accounts['test_user']['admin'],
              'support': 'Basic',
              'owner': Config.accounts['test_user']['owner'],
              'description': 'Test the Mongo',
              'contact': Config.accounts['test_user']['contact'],
              'life': 'medium',
              'backup_freq': 'Daily',
              'backup_life': '6',
              'backup_window': 'any',
              'pitr': 'n',
              'maintain': 'standard',
              'phi': 'No',
              'pitr': 'n',
              'db_vol': '/mydb/dbs_data',
              }
    params['dbtype'] = dbtype
    params['port'] = container_util.get_max_port()
    params['image'] = Config.info[dbtype]['images'][0][1]
    return params

def full_test(params):
    admin_db.init_db()
    print('Starting Test; Container Name: %s' % params['dbname'])
    if container_util.container_exists(params['dbname']):
        print('  Duplicate container: KILLING')
        result = container_util.kill_con(params['dbname'],
                                         Config.accounts[dbtype]['admin'],
                                         Config.accounts[dbtype]['admin_pass'],
                                         params['username'])
        time.sleep(5)
        print(result)
    print('  removing old directories')
    volumes.cleanup_dirs(params['dbname'])

    print('  Create container')
    res = mongodb_util.create_mongodb(params)
    print(res)

    bck_path = Config.backup_voll + '/' + params['dbname']
    print('  Test user account')
    if mongodb_util.auth_mongodb(params['dbuser'], params['dbuserpass'],
                                 params['port']):
        print("  - User exits!")
    else:
        print("  - User does not exits!")
    print("  - All Tests Complete! %s is up and running" % params['dbname']) 


def delete_test_container(params):
    dbtype = params['dbtype']
    result = container_util.kill_con(params['dbname'],
                                     Config.accounts[dbtype]['admin'],
                                     Config.accounts[dbtype]['admin_pass'],
                                     params['username'])
    print(result)


if __name__ == "__main__":
    dbtype = 'MongoDB'
    con_name = 'mongo-test'
    params = setup(dbtype, con_name)

    parser = argparse.ArgumentParser(prog='test_mongodbpy',
                                     description='Test MariaDB routines')
    parser.add_argument('--purge', '-d', action='store_true', default=False,
                        help='Delete test container')
    parser.add_argument('--backup', '-b', action='store_true', default=False,
                        help='backup mongodb')
    args = parser.parse_args()

    if args.purge:
        delete_test_container(params)
    elif args.backup:
        (cmd, mesg) = mongodb_util.backup_mongodb('mongo-test', 'User')
        print("backup command: %s\nResult: %s" % (cmd, mesg))
    else:
        full_test(params)
    print('- Tests Complete!')
