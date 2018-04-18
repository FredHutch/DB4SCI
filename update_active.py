#!/usr/bin/python
import os
import psycopg2
from docker import Client

import config as con

docker = con.fig.docker
cli=Client(con.fig.base_url)

def update_active():
    try:
	containers = cli.containers(all=True)
        jsonport=cli.inspect_container('pgjson')['HostConfig']['PortBindings']['5432/tcp'][0]['HostPort']
        jsonpw = [password for password in str(cli.inspect_container('pgjson')['Config']['Env']).split() \
            if 'PGPASSWORD' in password][0].split('=')[1][:-2]
        conn_string="dbname=pgjson user=pgjson host=" + con.fig.host + " port=" + \
            jsonport + " password=" + jsonpw
        conn=psycopg2.connect(conn_string)
        cur=conn.cursor()
        
        for con in containers:
            if 'Labels' in con and 'DBaaS' in con['Labels'] and con['Labels']['DBaaS']=='true':
               Name=con['Names'][0].strip('/')
               if con['State'] == 'running':
	           status='TRUE'
               else:
                   status='FALSE'
               sqlcmd= "update updated_containers set active=%s where container=\'%s\';" % (status, Name) 
               cur.execute(sqlcmd)
            conn.commit()
    except Exception,e:
        print("Error occured %s" % e)


if __name__ == "__main__":    
    update_active()
