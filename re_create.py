#!/usr/bin/env python
import re
import errno
import sys
import time
import datetime
import psycopg2
import logging
from docker import Client 
import mydb.config as config

'''re_create is a command line tool to create the docker run command
for an existing database container created by MyDB.
At present this code is broken.
'''

pwfile = '/root/.pgpass'
dbname = 'mydb_admin'

def docker_inspect(con_name):
    cli=Client(base_url=config.var.base_url)
    try:
        insp = cli.inspect_container(con_name)
    except Exception as e:
        return None
    return insp

def get_pw(dbname):
    with open(pwfile, 'r') as f:
        for line in f:
            host,port,service,dbuser,password = line.split(':')
            if service == dbname:
                return [host,port,dbuser,password]
    return 'not found' 

def Newest_CreatedAt(rows):
    newest = 0.0
    rec = None
    for record in rows:
        s = record[0]['State']['StartedAt']
        created = re.sub(r"\d\d\d\dZ", "Z", s)
        timestamp = time.mktime(datetime.datetime.strptime(created, 
                                "%Y-%m-%dT%H:%M:%S.%fZ").timetuple())
        if timestamp > newest:
            newest = timestamp
            rec = record
    return rec 

def run_command(data):
    """re-create the run command from mydb_admin db 'Info'"""
    info = data[0][0]['Info']
    image = info['Image']
    if 'neo4j' in image:
        dbtype = 'Neo4j'
        config_dat = config.var.info[dbtype]
        Ports = '-p %s:%s ' % (info

    create_cmd = "%s run -d " % config.var.docker
    create_cmd += Ports 
    create_cmd += '--name %s --restart on-failure -e POSTGRES_USER='%s' \
        -e POSTGRES_DB=%s -e PGPASSWORD='%s' -e POSTGRES_PASSWORD='%s' \
        -e TZ=America/Los_Angeles \
        -l SUPPORT=%s -l OWNER=\"%s\" -l DESCRIPTION=\"%s\" \
        -l DBaaS=true -l CONTACT=\"%s\" -l SIZE=%s -m=%s \
        -l CONNECTIONS=%s -l LIFE=%s -l BACKUP_FREQ=%s -l BACKUP_LIFE=%s \
        -l BACKUP_WINDOW=%s -l PITR=%s -l MAINTAIN=%s -l PHI=%s  -l LONGPASS='%s' \
        -v %s/%s:/var/lib/postgresql/data \
        -v %s/%s:/var/lib/postgresql/backup \
        %s 2>/dev/null" % ()

def container_create(inspect):
    """ XXX """
    bindings = inspect['HostConfig']['PortBindings']
    for p in bindings:
        port = bindings[p][0]['HostPort']
    con_name = inspect['Name'][1:]

    env = inspect['Config']['Env']
    mem = inspect['HostConfig']['Memory']
    memlimit = str(mem) + 'b'  
    dbuser = [user for user in env if 'POSTGRES_USER' in user][0].split('=')[1]
    dbname = [user for user in env if 'POSTGRES_DB' in user][0].split('=')[1]
    dbuserpass = [user for user in env if 'PGPASSWORD' in user][0].split('=')[1]
    postgres_pass = [user for user in env if 'POSTGRES_PASSWORD' in user][0].split('=')[1] 
 
    labels = inspect['Config']['Labels']

    create_cmd = "%s run -d -p %s:%s:5432/tcp --name %s --restart on-failure -e POSTGRES_USER='%s' \
        -e POSTGRES_DB=%s -e PGPASSWORD='%s' -e POSTGRES_PASSWORD='%s' \
        -e TZ=America/Los_Angeles \
        -l SUPPORT=%s -l OWNER=\"%s\" -l DESCRIPTION=\"%s\" \
        -l DBaaS=true -l CONTACT=\"%s\" -l SIZE=%s -m=%s \
        -l CONNECTIONS=%s -l LIFE=%s -l BACKUP_FREQ=%s -l BACKUP_LIFE=%s \
        -l BACKUP_WINDOW=%s -l PITR=%s -l MAINTAIN=%s -l PHI=%s  -l LONGPASS='%s' \
        -v %s/%s:/var/lib/postgresql/data \
        -v %s/%s:/var/lib/postgresql/backup \
        %s 2>/dev/null" % (
        config.var.docker, config.var.container_ip, port, dbname, dbuser, dbname,
        dbuserpass, dbuserpass, 
        labels['SUPPORT'], 
        labels['OWNER'], 
        labels['DESCRIPTION'],
        labels['CONTACT'], 
        labels['SIZE'], memlimit, labels['CONNECTIONS'], labels['LIFE'],
        labels['BACKUP_FREQ'], labels['BACKUP_LIFE'], labels['BACKUP_WINDOW'], labels['PITR'], labels['MAINTAIN'],
        labels['PHI'], labels['LONGPASS'], config.var.dbvol, con_name, config.var.backupvol, con_name, config.var.postgres_images[1])
  
    print "%s: Created: %s" % (con_name, inspect['Created'])
    print ' '.join(create_cmd.split()) + '\n'

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "usage: " + sys.argv[0] + " [container name]"
        sys.exit(0)
    container = sys.argv[1]
    data = admin_db.get_container_data(container) 
    if not data:
       print "Could not find the container in admin DB"
       sys.exit()
    info = data['Info']
    run_command(info)
