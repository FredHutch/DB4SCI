#!/bin/bash

# create admindb
# admindb must be created before dbaas can be run
# Application expects port to be 32009

docker run \
--name=mydb_admin \
--detach  \
--restart on-failure \
--publish=140.107.117.194:32009:5432/tcp \
-m=1GB \
--volume=/mydb/postgres_dbs/mydb_admin:/var/lib/postgresql/data \
--volume=/mydb/db_backups/mydb_admin:/var/lib/postgresql/backup \
-e POSTGRES_DB=mydbadmin \
-e POSTGRES_USER='mydbadmin' \
-e PGPASSWORD='db4docker' \
-e TZ=America/Los_Angeles \
--label DBaaS=true \
postgres:9.6.1
