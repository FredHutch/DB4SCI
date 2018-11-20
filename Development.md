## DBaaS Development Notes 

### Overview
The production instance of DBaaS application uses Nginx for web proxy. 
The Nginx web proxy is deployed as a separate Docker container. Nginx listens on ports 80 and 443. 
Nginx proxies web requests to dbaas via uWSGI on port 5000. Nginx maintains the SSL certificates.
uWSGI is installed in the same container as the DBaas flask application. The link between Nginx and uWSGI is defined in the file: <docker-compose.yml>. 
The dbaas Flask application listens on port 5000 using the uWSGI protocol.

### Prodution and Development
Production and development instance run on seperate systems. The differances between production and development effect the Nginx web interface and not the application code.  Nginx configurations are defined in two subdirectories <prod> and <dev>.  The environment variable DBAAS_ENV must be set to [prod, dev, demo] for docker build to work.

```bash
export DBAAS_ENV=prod
# OR
export DBAAS_ENV=dev
```

### SSL
The SSL certs can be different between production and development. Place production certs in prod/nginx/ssl
and development
certs in dev/nginx/ssl directories.
Production and developemnt domains are seperated by folder name for nginx. 

### DBaas
All differences between produciton and development for DBaas are contained in the config.py file.
Prod and Dev are defined as classes in the config file. 

### Database Container Management 
The need to support multible different versions of database containers is supported. 
Docker images used by the application are configured in mydb/config.py. 

```python
# images: List of Docker Images
# first column is 'Display Name'
# second column is 'image name'
# firt row of image is default
info = {'Postgres': {'pub_ports': [5432],
                     'backupdir': '/var/lib/postgresql/backup',
                     'volumes': [
                            ['DBVOL', '/', '/var/lib/postgresql/data'],
                            [backupvol, '/', '/var/lib/postgresql/backup'],
                         ],
                     'command': 'postgres',
                     'dbengine': 'Postgres',
                     'images': [
                             ['Postgres 9.6.10', 'postgres:9.6.10'],
                             ['Postgres 10.5', 'postgres:10.5'],
                          ]},
```

### Adminstrative Database
DB4SCI maintains application status in its own Postgres Database (mydb_admin).
All actions to database continers are logged in the database; create
container, restart, delete, backup. The admin_database
has four tables: Container, State, Log and Backup_log. The state table
contains the names of running containers and is used for backup and recovery.
DB4Sci will create the mydb_admin container if it is not running, typically
this is done once the first time the application is started. Full backups are
made of mydb_admin. mydb_admin is a critical part of the application, should
it be harmmed the database should be recovered.          

### History
Robert McDermott created the initial application in one weekend during the
spring of 2016. The initial
application was called 'postgres_container_mgmt'.  Mija Lee supported all the
the early Postgres support and coding for creating, configuring and backups
for Postgres. John Dey is the current maintainer.

The primary Flask daemon is called dbaas (Data Base as a service).
The applacation was renamed from postgres_contianer_mgmt to mydb. This name
change reflected the general use case of creating any type of database
container, not just PostgreSQL.  Support for Maria, Mongo and Neo4j were
added based on user requests. It was always the intent to make MyDB a public
repository but the name MyDB was not available. The second name change to
DB4Sci was result of making the code public. DB4Sci logo was created by the
publication department at the Fred Hutch.

The name mydb is used throughout the code, mydb is short and easy to type and
will remain within the code. The name DB4Sci will be used when refering to the
application.
