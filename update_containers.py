#!/usr/bin/python
import os
import psycopg2
import config as con
import optparse
from docker import Client

docker = con.fig.docker
cli=Client(con.fig.base_url)

# json objects are added into pgjson.containers in the postgres_create
# This program is only for adding an entry into pgjson.containers
# when there has been some type of failure in the postgres_create 
# code. It is not meant to run in the cron. 


def update_containers(name):
    try:
        #create json for new docker container to insert into json db
        json=os.popen("%s inspect %s" % (docker, name)).read().rstrip()[1:-1]
        jsonport=cli.inspect_container('pgjson')['HostConfig']['PortBindings']['5432/tcp'][0]['HostPort']
        #dropping last two characters which are ,' due to lambda
        jsonpw = [password for password in str(cli.inspect_container('pgjson')['Config']['Env']).split() \
            if 'PGPASSWORD' in password][0].split('=')[1][:-2]
        conn_string="dbname=pgjson user=pgjson host=" + con.fig.host + " port=" + \
            jsonport + " password=" + jsonpw
        conn=psycopg2.connect(conn_string)
        cur=conn.cursor()
        cur.execute("insert into containers(data) values('%s');" % (json,))
        conn.commit()
    except Exception,e:
        print("Error occured %s" % e)


if __name__ == "__main__":    
    p=optparse.OptionParser(usage="usage: %prog --name=<container/dbname>" , version="%prog 1.0")
    p.add_option('-n', '--name',  action='store', type='string', dest='name', help='Name of the container')
    opt, args=p.parse_args()
    update_containers(opt.name)
