#!/usr/bin/python
import os
from config import Config

"""DB4SCI can depoly containers on different storage volumes.
Access to Volumes can be assigned to users.
Create a new list of volumes based on username.  
used by mydb_views to generate general_form.html
  volume[2] dbtype
  volume[3] dbusers
"""

def volumes(dbtype, username):
    new_vols = []
    Admin = False
    if username in Config.admins:
        Admin = True
    for volume in Config.data_volumes:
        db_list = volume[2]
        user_list = volume[3]
        if 'ALL' in db_list or dbtype in db_list:
            if (('ALL' in volume[3]) or 
                ('Admin' in volume[3] and Admin) or
                (username in volume[3])):
     
                new_vols.append(volume)
    return new_vols

def cleanup_dirs(con_name):
    """remove old directories used by a container
       this is dangerous only use with testing or debugging
    """
    db_vol = None
    backup_vol = "{}/{}".format(Config.backupvol, con_name)
    for vol in Config.data_volumes:
        db_vol = "{}/{}".format(vol, con_name)
        if os.path.isdir(db_vol):
            break
    if db_vol:
        for top in [db_vol, backup_vol]:
            for root, dirs, files in os.walk(top, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
    else:
        print("DEBUG: Data Volume for {} not found".format(con_name))

if __name__ == '__main__':
    vol_lst = volumes('Postgres', 'admin')
    print('Test1: Postgres, admin')
    for v in vol_lst:
        print('%20s %s' % (v[0], v[1]))

    print('\n\nTest2: MariaDB, admin')
    vol_lst= volumes('MariaDB', 'admin')
    for v in vol_lst:
        print('%20s %s' % (v[0], v[1]))

    print('\n\nTest2: Demo Mode')
    vol_lst= volumes('Postgres', 'demo')
    for v in vol_lst:
        print('%20s %s' % (v[0], v[1]))
