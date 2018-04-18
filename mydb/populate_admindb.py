#!/usr/bin/env python
import re
import time
import datetime
import container_util
import admin_db
from models import *

""" Do not distrubute this module.  It is only needed to populate the
mydb_admin database from docker inspect.  It is only needed as a tool
to convert the original postgresdb system which was not created or
managed with mydb_admin database.
"""


def build_admindb():
    """Note: Run this only Once!
    Initial creation for the administrative DB
    query docker inspect for all running instances
    add info = {} to inspect data
    create Containers table and insert all inspect data.
    """
    con_list = container_util.list_all_containers()
    params = {}
    for con in con_list:
        inspect = container_util.inspect_con(con['Names'][0])
        con_name = con['Names'][0][1:]
        if con_name != 'mydb_admin' and inspect['State']['Status'] == 'running':
            params['Port'] = con['Ports'][0]['PublicPort']
            params['Image'] = con['Image']
            print('Adding: %s image: %s port: %d' % (con_name,
                                                     params['Image'],
                                                     params['Port']))
            # temp = inspect['State']['StartedAt']
            # started = re.sub(r"\d\d\d\dZ", "Z", temp) 
            # timestamp = time.mktime(datetime.datetime.strptime(started,
            #                     "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
            c_id = admin_db.add_container(inspect, params)
            admin_db.add_container_log(c_id, con_name, "created",
                                       'initialized by build_admindb')

if __name__ == '__main__':
    print('Warning!  This should only be run once. '),
    print('  too create mydb_admin database from "docker inspect"')
    build_admindb()
