# DB4Sci Database Restore Procedures
DB4Sci is a containerized database service. Users select the backup
service they require at the time the database is created. Daily, Weekly
or None are backup schedule options. Native database backup tools are used to
backup PostgreSQL and MariaDB. Backup data files are written to S3.

#### DB4Sci Environment
DB4Sci can be deployed on-prem with physical hardware or on an EC2 instance.
The application server should be the same system that the application URL
resolves too.  Example: mydb.fredhutch.org 
The only way to access the application container is from
the container host. DB4Sci application container is named **dbaas**.
All database recovery tasks need to be performed from the **dbaas**
container.

To access **dbaas** become root on your application host. Access
the container shell with docker command. 
```
docker exec -ti dbaas bash
```
The shell environment of **dbaas** has the AWS access keys defined in
the shell environment and the AWS software awscli is installed. The bucket name
is also configured in the environment and can be accessed with `${AWS_BUCKET}`
with Bash.

Backups are written to S3 as they are completed. S3 bucket prefixes
are based on container name and backup datetime.
Bucket prefix format used used for all database backups:  
```
Bucket URL / prod / container Name / Container Name_YYY-MM-DD_HH-MM-SS / 
Example URL: s3://scicomp-db4sci-backup/prod/mydb_admin/mydb_admin_2018-11-13_02-07-02/mydb_admin.sql
```

To list backup targets for a container run this AWS command from **dbaas**.
The slash at the end of the URL will
list the files in the prefix.  All instances of DB4Sci
use the administrative database **mydb_admin**.
```
aws s3 ls ${AWS_BUCKET}/mydb_admin/
```

#### DB4Sci Storage Environment
Each database container has its own unique volumes maps for data and backup.
The main application container **dbaas** has the root of all the storage
volumes which are used by all container instances. When restoring files
from the **dbaas** container they can be copied directory to the source 
volume used by a container.
Consult the volume mapping in `mydb/config.py` for the volume configuration.
Example of volume mapping which used the directory `/mydb` to store container
data:
```
DB4Sci:/mydb/db_data/mydb_admin  -> mydb_admin:/var/lib/postgresql/data```
DB4Sci:/mydb/db_data/demo1 -> demo1:/var/lib/postgresql/data
```

#### Recovery Scenarios
This document describes how to recover databases with the DB4Sci application
environment installed and running. If the application host is not available
use the DR documentation to recreate a running environment. 

 * [DR Procedures](DR.md)

 * [PostgreSQL Restore](PostgreSQL-restore.md)
 * [MariaDB Restore](MariaDB-restore.md)

# from a rhino host
ml PostgreSQL
ml awscli

export AWS_PROFILE=DB4Sci
# Step One replay the mydb_admin.sql file
aws s3 cp s3://fh-div-adm-scicomp-mydb-backup/prod/mydb_admin/mydb_admin_2018-11-13_02-07-02/mydb_admin.sql - |\
 psql -h db4sci-dev.fhcrc.org -p 32009 -d mydb_admin -U db4sci

# Step two recover the data 

aws s3 cp ${bucket}mydb_admin/mydb_admin_2018-11-15_02-07-02/mydb_admin_mydb_admin.dump - | \
pg_restore -h db 4sci-dev.fhcrc.org -p 32011 -d demo1 -U jfdey

# Step three recover the control file

# copy from S3 to rhino
aws s3 cp ${bucket}mydb_admin/mydb_admin_2018-11-15_02-07-02/postgresql.auto.co
nf .
# copy from rhino to DR host db4sci-dev
scp postgresql.auto.conf db4sci-dev.fhcrc.org:/var/tmp

# copy from DR host (db4sci-dev) to container
docker cp /var/tmp/postgresql.auto.conf demo1:/var/lib/postgresql/data

The container needs to be restarted in order to read the control file. The 
Control file has alter system commands in it.
