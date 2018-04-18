#!/usr/bin/python
import time
import psycopg2
import argparse
import postgres_util
import container_util
import admin_db
import volumes
from send_mail import send_mail

import local_config


def full_test(params):
    admin_db.init_db()
    con_name = params['dbname']
    dbtype = params['dbtype']
    print('Starting %s Test; Container Name: %s' % (dbtype, con_name))
    if container_util.container_exists(con_name):
        print('  Duplicate container: KILLING')
        result = container_util.kill_con(con_name,
                                         local_config.var.accounts[dbtype]['admin'],
                                         local_config.var.accounts[dbtype]['admin_pass'],
                                         params['username'])
        time.sleep(5)
        print(result)
    print('  removing old directories')
    volumes.cleanup_dirs(con_name)
    print('  Create container')
    result = postgres_util.create(params)
    print('  Create result: %s' % result)
    port = params['port']

    #
    #  Admin DB checking
    #
    print('  Check Admin DB log for "create"')
    admin_db.display_container_log(limit=1)
    print('  Check Admin DB for State entry')
    info = admin_db.get_container_state(con_name)
    print('     Name: %s ' % info.name),
    print('State: %s ' % info.state),
    print('TS: %s ' % info.ts),
    print('CID: %d' %  info.c_id)
    print('  Check Admin DB for Container Info')
    info = admin_db.display_container_info(con_name)
    print('Info: %s' % info)

    print('  Postgres Show All')
    postgres_util.showall(params)

    print("\n=========")
    print(" - Test Accounts\n")
    print("=========")
    admin_user = local_config.var.accounts[dbtype]['admin']
    admin_pass = local_config.var.accounts[dbtype]['admin_pass']
    test_user = local_config.var.accounts['test_user']['admin']
    test_pass = local_config.var.accounts['test_user']['admin_pass']
    for dbuser, dbuserpass in [[test_user, test_pass],
                               ['svc_'+test_user, params['longpass']],
                               [admin_user, admin_pass]]:
        auth = postgres_util.auth_check(dbuser,
                                        dbuserpass,
                                        port)
        if auth:
            print('User %s verified!' % dbuser)
        else:
            print('user account not valid: %s' % dbuser)
    print(" - Test Complete")


def populate(params):
    dbTestName = 'testdb'
    dbtype = params['dbtype']
    conn_string = "dbname='%s' " % params['dbname']
    conn_string += "user='%s' " % local_config.var.accounts[dbtype]['admin']
    conn_string += "host='%s' " % local_config.var.container_host
    conn_string += "port='%d' " % params['port']
    conn_string += "password='%s'" % local_config.var.accounts[dbtype]['admin_pass']
    print(' - Populate with test data: ')
    try:
        conn = psycopg2.connect(conn_string)
    except:
        print "I am unable to connect to the database"
    conn.set_isolation_level(0)
    cur = conn.cursor()
    print(' - Create DB: ' + dbTestName)
    cur.execute("CREATE TABLE t1 (id serial PRIMARY KEY, num integer, data varchar);")
    cur.execute("INSERT INTO t1 (num, data) VALUES (%s, %s)", 
                (100, "table t1 in Primary database"))
    cur.execute("CREATE DATABASE " + dbTestName)
    conn.close()

    target = "dbname='%s'" % params['dbname']
    testdb = "dbname='%s'" % dbTestName 
    conn2 = conn_string.replace(target, testdb)
    print(' - Connect to new DB: ' + conn2)
    conn = psycopg2.connect(conn2)
    cur = conn.cursor()
    print(' - Create Table and Insert ')
    cur.execute("CREATE TABLE t2 (id serial PRIMARY KEY, num integer, data varchar);")
    cur.execute("INSERT INTO t2 (num, data) VALUES (%s, %s)", 
                (100, "Important test data in t2"))
    conn.commit()
    cur.close()
    print(' - Populate Success')
 
def delete_test_container(dbtype, con_name):
    print("\n=========")
    print(" - Removing Container")
    print("=========")
    result = container_util.kill_con(con_name,
                                     local_config.var.accounts[dbtype]['admin'],
                                     local_config.var.accounts[dbtype]['admin_pass'])
    print(result)

def setup(dbtype, con_name):
    params = {'dbname': con_name,
              'dbuser': local_config.var.accounts['test_user']['admin'],
              'dbtype': dbtype,
              'dbuserpass': local_config.var.accounts['test_user']['admin_pass'],
              'support': 'Basic',
              'owner': local_config.var.accounts['test_user']['owner'],
              'description': 'Test the Dev',
              'contact': local_config.var.accounts['test_user']['contact'],
              'life': 'medium',
              'backup_type': 'User',
              'backup_freq': 'Daily',
              'backup_life': '6',
              'backup_window': 'any',
              'pitr': 'n',
              'maintain': 'standard',
              'phi': 'No',
              'pitr': 'n',
              'username': local_config.var.accounts['test_user']['admin'],
              'image': local_config.info[dbtype]['images'][1][1],
              'db_vol': '/mydb/dbs_data',
              }
    return params

if __name__ == "__main__":
    dbtype = 'Postgres'
    con_name = 'postgres-test'
    params = setup(dbtype, con_name)
    # paramd['db_vol'] = '/mydb/encrypt',

    parser = argparse.ArgumentParser(prog='test_postgres.py',
                                     description='Test %s routines' % dbtype)
    parser.add_argument('--purge', '-d', action='store_true', default=False,
                        help='Delete test container')
    parser.add_argument('--backup', '-b', action='store_true', default=False,
                        help='backup %s' % params['dbname'])
    args = parser.parse_args()

    if args.purge:
        delete_test_container(dbtype, con_name)
    elif args.backup:
        (cmd, mesg) = postgres_util.backup(params)
        print("Command: %s\nBackup result: %s" % (cmd, mesg))
    else:
        full_test(params)
        populate(params)
        postgres_util.backup(params)
    print('- Tests Complete!')
