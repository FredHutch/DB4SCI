#!/usr/bin/python
import time
import logging
import logging.handlers
from docker import Client
import mydb.admin_db as admin_db
import mydb.postgres_util as postgres
import mydb.mariadb_util as mariadb
import mydb.mongodb_util as mongodb
import mydb.container_util as container_util
import mydb.config as config
import mydb.secrets as secrets

"""Fix info data in admin_db

   Image is only available from docker ps, and was not
   put into docker inspect.  Use docker ps data to populate
   the 'info' data in admin_db.
"""


def fix_info():
    dbtype = 'Postgres'

    logging.info("Let's fix info")
    t = time.localtime()
    ts = "%s-%02d-%02d_%02d-%02d-%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
    cli = Client(base_url=con.fig.base_url)
    docker_list = cli.containers()
    inspect = {}
    for con in docker_list:
        inspect[con['Names'][0][1:]] = con['Image']

    admin_list= admin_db.list_containers()
    for (c_id, con_name) in admin_list:
        data = admin_db.get_container_data('', c_id)[0].data
        info = data['Info']
        print("%-30s %-10s %-35s %s" % (info['Name'], info['dbengine'], info['Image'], info['BACKUP_FREQ']))
        #if 'Image' in data['Info']:
        #    continue
        #else:
        #    image = inspect[con_name]
        #info['Image'] = image
        #admin_db.update_container_info(c_id, info, who='dbaas')

if __name__ == "__main__":

    fix_info()
