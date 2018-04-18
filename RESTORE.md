# Restore Procedures
All commands are issued from DBaas. To get to that container issue the following command:
`sudo docker exec -ti dbaas bash env TERM=linux bash -l `

In the code below, replace 

- portnum with the number of the port of the new database container
- container with the name of the container that you are replicating
- timestamp with the appropriate timestamp
- user with one of the superusers that on the new container for which you have the password. A docker inspect on the container will provide you with a username and password if needed.
- newdb is the new database to which you are restoring
- olddb is the old database from which your backup was generated.

## To restore a database from backup still on the system
1) Determine the correct backup to restore from /var/db_backups/container
2) Create database with new name
```
psql -h mydb -p portnum postgres user 
postgres=# create database newdb;
CREATE DATABASE
```
3)  Restore the database. 
```pg_restore -h mydb -p portnum -d newdb -e /var/db_backups/container/olddb_timestamp.dump -U user```
4) Do basic queries to ensure database has been restored properly, including check on permissions. 
5) If requested, drop old database, rename new database to old database name. You can restore in place if needed, but this is the safer way to restore, assuming you have adequate disk space. 
```
psql -h mydb -p portnum postgres user
postgres=# drop database olddb;
DROP DATABASE
postgres=# alter database newdb rename to olddb;
ALTER DATABASE
```
## To restore a database from s3
1) Determine the correct backup to restore. You can do this with through `aws s3 ls -recursive s3://YourBucket` or through the DBaas UI.
2) Get file from s3. Note there are costs associated with downloading files
`aws s3 cp s3://YourBucket/container/olddb_timestamp /var/db_backups
`
3) Follow steps describe above to restore the database and swap the names, if requested.

## To restore a database server
1) Create new database server using the UI. If requested, obtain information from pgjson.pgjson to create a container with the same initial settings. Password for pgjson can be obtained by doing a docker inspect of the container.
```
psql -h mydb -p 32010 -U pgjson pgjson
pgjson=# select data->'Config'->'Env' from containers where data->>'Name'='/container'; 
pgjson=# select data->'Config'->'Labels' from containers where data->>'Name'='/container';
```
2)  Identify the correct backups from either s3 or /mydb/db_backup
3) Copy file with any postgres system changes into the new container's data directory. If there are differences between the files, restart the container to take the new settings.
```
diff /var/db_backups/container/container_auto.conf /var/postgres_dbs/container/postgresql.auto.conf
cp /var/db_backups/container/container_auto.conf /var/postgres_dbs/container/postgresql.auto.conf
docker restart container
```
4) Run pg_dumpall output through psql to create all users and other global database objects. 
```
psql -h mydb -p portnum -f /var/db_backups/container/container_timestamp.sql -U user
```
There will be errors as a result of trying to create users which were created during the container post processing step (e.g., user pgdba and postgres). If they look like the following they can be ignored; otherwise investigate.
`
ERROR:  role "pgdba" already exists
`
5) Create databases on the new database server. In most cases, when you create a new postgres container, you will want the newdb to be the same name as the olddb, but this will depend upon your circumstances. 
```
psql -h mydb -p portnum postgres user 
postgres=# create database newdb;
CREATE DATABASE
```
6)  Restore each of the databases through pg_restore from inside the appropriate container
`pg_restore -h mydb -p portnum -d newdb -e /var/lib/postgresql/backup/olddb_timestamp.dump -U user`




