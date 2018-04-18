#!/usr/bin/python
import os
import local_config

"""MyDB can depoly containers on different storge volumes.
Access to Volumes can be assigned to users.
Create a new list of volumes based on username.  
used by mydb_views to generate general_form.html
  volume[2] dbtype
  volume[3] dbusers
"""

def volumes(dbtype, username):
    new_vols = []
    for volume in local_config.var.data_volumes:
        if ('ALL' in volume[2]) or (dbtype in volume[2]):
            if ('ALL' in volume[3]) or (username in volume[3]):
                new_vols.append(volume)
    return new_vols

def cleanup_dirs(con_name):
    """ remove old directories used by a container
       this is dangerous only use with testing or debug
    """
    db_vol = local_config.var.data_volumes[0][1]
    for top in ["%s/%s" % (db_vol, con_name),
                "%s/%s" % (local_config.var.backup_vol, con_name)]:
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

if __name__ == '__main__':
    vol_lst = volumes('Postgres', 'admin')
    print('Test1: Postgres, admin')
    for v in vol_lst:
        print('%20s %s' % (v[0], v[1]))


    print('\n\nTest2: MariaDB, admin')
    vol_lst= volumes('MariaDB', 'admin')
    for v in vol_lst:
        print('%20s %s' % (v[0], v[1]))
