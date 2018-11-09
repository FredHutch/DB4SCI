#!/usr/bin/env python
import os
import sys
import argparse
import time
import neo4j_util
import container_util
import admin_db
import volumes
from config import Config
import neo4j.v1 as neo4j
from neo4j.v1 import GraphDatabase, basic_auth

"""
    Test Neo4j docker functionality.  All routines from neo4j_util are tested.
    - Create container
      - set password for default admin account
      - create user accounts
      - create storage
      - test accounts
    - Populate Neo4j with data
    - Backup Neo4j
    - Remove container
      
    params['port_bindings'] = {7473: ('140.107.117.198', 32011), 7474: ('140.107.117.198', 32012), 7687: ('140.107.117.198', 32013)}
    host_ip, bolt_port = params['port_bindings'][7687]
"""


def test_create(params):
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
    res = neo4j_util.create(params)
    print(res)
    params['port'] = params['port_bindings'][7687][1]
    print('  Bolt Port: %d' % params['port'])

    print('  Test user account')
    if neo4j_util.auth_check(params['dbuser'], params['dbuserpass'],
                                 params['port']):
        print("  - User exits!")
    else:
        print("  - User does not exits!")
    status =  neo4j_util.create_account('keith', 'neoTester', params['port'])
    if status:
        print("  Created test account for Keith")
    else:
        print("  Badness: unable to create account for Keith")
    print("  - Create Neo4j Complete!")


def test_popluate(params):
    """Write data to Neo4j"""
    bolt_port = params['port_bindings'][7687][1]
    url = 'bolt://' + Config.container_ip + ':' + str(bolt_port)
    password = Config.accounts['Neo4j']['admin_pass']

    try:
        driver = GraphDatabase.driver(url, auth=basic_auth("neo4j", password))
    except:
        return False
    session = driver.session()
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Arthur", "title": "King"})
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Guinevere", "title": "Wife"})
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Kaius", "title": "knight"})
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Beduerus", "title": "knight"})
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Guaiguanus", "title": "knight"})
    session.run("CREATE (a:Person {name: {name}, title: {title}})",
              {"name": "Round Table", "title": "Court"})
    session.close()
    print(' - Populate Test Success')
    
def test_delete(dbtype, dbname):
    result = container_util.kill_con(dbname,
                                     Config.accounts[dbtype]['admin'],
                                     Config.accounts[dbtype]['admin_pass'])
    print(result)


def setup(dbtype, con_name):
    params = {'dbname': con_name,
              'dbtype': dbtype,
              'dbuser': Config.accounts['test_user']['admin'],
              'dbuserpass': Config.accounts['test_user']['admin_pass'],
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
              'image': Config.info[dbtype]['images'][0][1],
              'db_vol': '/mydb/dbs_data',
              }
    return params

if __name__ == "__main__":
    dbtype = 'Neo4j'
    con_name = 'neo4j-test'
    params = setup(dbtype, con_name)

    parser = argparse.ArgumentParser(prog='neo4j_test.py',
                                     description='Test MariaDB routines')
    parser.add_argument('--purge', '-d', action='store_true', default=False,
                        help='Delete test container')
    parser.add_argument('--backup', '-b', action='store_true', default=False,
                        help='backup %s' % params['dbname'])
    args = parser.parse_args()

    if args.purge:
        delete_test_container(dbtype, con_name)
    elif args.backup:
        (cmd, mesg) = neo4j_util.backup(params)
        print("Command: %s\nResult: %s" % (cmd, mesg))
    else:
        test_create(params)
        test_popluate(params)
