#!/usr/bin/env python
import admin_db


""" when schema changes are needed to admin_db data
    Add new column to the "Info" field of admin_db
    admin_db is a json column. so its easy to add additional metadata since 
    no structural changes need to be made to the database.
"""

def add_info_field(key, value):
    """ Add key value to all existing DB4SCI containers
    """
    containers = admin_db.list_containers() 
    for [cid, name] in containers:
        print('%3d Update: %s' % (cid, name))
        data = admin_db.get_container_data('', cid)
        info = data['Info']
        if key in info: continue
        info[key] = value
        admin_db.update_container_info(cid, info, 'admUser')



if __name__ == '__main__':
    add_info_field('DBVOL', '/mydb/dbs_data')
    
