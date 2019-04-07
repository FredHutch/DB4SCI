#!/usr/bin/env python
import os
import sys
import argparse
import time
import mariadb_util
import container_util
import admin_db
import volumes
from config import Config


def full_test(params):
    admin_db.init_db()
    dbtype = params['dbtype']
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
    res = mariadb_util.create_mariadb(params)
    print(res)

    print('  Test user account')
    if mariadb_util.auth_mariadb(params['dbuser'],
                                 params['dbuserpass'],
                                 params['port']):
        print("  - User exits!")
    else:
        print("  - User does not exits!")
    print("  - Tests Complete!")


def delete_con(params):
    result = container_util.kill_con(params['dbname'],
                                     Config.accounts['test_user']['admin'],
                                     Config.accounts['test_user']['admin_pass'],
                                     params['username'])
    print(result)


if __name__ == "__main__":
    con_name = 'mariadb-test'
    dbtype = 'MariaDB'
    params = {'dbname': con_name,
              'dbuser': Config.accounts['test_user']['admin'],
              'support': 'Basic',
              'owner': Config.accounts['test_user']['owner'],
              'description': 'Test the Dev',
              'contact': Config.accounts['test_user']['contact'],
              'life': 'medium',
              'backup_type': 'User',
              'backup_freq': 'Daily',
              'backup_life': '6',
              'backup_window': 'any',
              'maintain': 'standard',
              'phi': 'No',
              'pitr': 'n',
              'username': Config.accounts['test_user']['admin'],
              'db_vol': '/mydb/dbs_data',
              }
    params['dbuserpass'] = unicode(Config.accounts['test_user']['admin_pass'])
    params['dbtype'] = dbtype
    params['port'] = container_util.get_max_port()
    params['image'] = Config.info[dbtype]['images'][0][1]

    parser = argparse.ArgumentParser(prog='mariadb_test.py',
                                     description='Test MariaDB routines')
    parser.add_argument('--purge', '-d', action='store_true', default=False,
                        help='Delete test container')
    parser.add_argument('--backup', '-b', action='store_true', default=False,
                        help='backup %s' % params['dbname'])
    args = parser.parse_args()

    if args.purge:
        delete_con(params)
    elif args.backup:
        (cmd, mesg) = mariadb_util.backup_mariadb(params)
        print("Command: %s\nBackup result: %s" % (cmd, mesg))
    else:
        full_test(params)
