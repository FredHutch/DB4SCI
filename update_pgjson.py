#!/usr/bin/python
import psycopg2
import logging
import textwrap
import config as con
from docker import Client

import config as con

def add_new():
    sqlcmd=textwrap.dedent("""\
	insert into updated_containers select 
	trim(leading '/' from data->>'Name':: text) as container,
	TRUE as active,
	a.data->'HostConfig'->'PortBindings'->'5432/tcp'->0->>'HostPort'::text as port,
        a.data->'Config'->'Labels'->>'BACKUP_FREQ'::text as backup_freq,
        a.data->'Config'->'Labels'->>'BACKUP_LIFE'::text as backup_life,
        a.data->'Config'->'Labels'->>'BACKUP_WINDOW'::text as backup_window,
        a.data->'Config'->'Labels'->>'CONNECTIONS'::text as connections,
        a.data->'Config'->'Labels'->>'CONTACT'::text as contact,
        a.data->'Config'->'Labels'->>'DESCRIPTION'::text as description,
        a.data->'Config'->'Labels'->>'LIFE'::text as life,
        a.data->'Config'->'Labels'->>'MAINTAIN'::text as maintain,
        a.data->'Config'->'Labels'->>'OWNER'::text as owner,
        a.data->'Config'->'Labels'->>'PHI'::text as phi,
        a.data->'Config'->'Labels'->>'PITR'::text as pitr,
        a.data->'Config'->'Labels'->>'SIZE'::text as size,
        a.data->'Config'->'Labels'->>'SUPPORT'::text as support      
	from containers as a left join
        updated_containers as b 
        on trim (leading '/' from a.data->>'Name') = b.container where b.container is null;
        """)
    cli=Client(base_url=con.fig.base_url)
    jsonport=cli.inspect_container('pgjson')['HostConfig']['PortBindings']['5432/tcp'][0]['HostPort']
    jsonpw = [password for password in str(cli.inspect_container('pgjson')['Config']['Env']).split() \
        if 'PGPASSWORD' in password][0].split('=')[1][:-2]
    conn_string="dbname=pgjson user=pgjson host=" + con.fig.container_host +\
        " port=" + jsonport + " password=" + jsonpw
    try:
        connection=psycopg2.connect(conn_string)
        cur=connection.cursor()
        cur.execute(sqlcmd)
        connection.commit()
    except Exception, e:
        logging.error("An error occurred connecting to %s: message %s; connect string:", con, e, connect)

if __name__ == "__main__":
    FORMAT = "%(asctime)s %(module)s:%(levelname)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT, filename=con.fig.admindb_log)

    add_new()
    logging.info("admindb updated")

