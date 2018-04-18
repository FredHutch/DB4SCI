## DBaaS Development Notes 

### Overview
The production instance of DBaaS application uses Nginx for web proxy. 
The Nginx web proxy is deployed as a separate Docker container. Nginx lists on ports 80 and 443. 
Nginx proxies web requests to dbaas via uWSGI on port 5000. Nginx maintains the SSL certificates.
uWSGI is installed in the same container as the DBaas flask application. The link between Nginx and uWSGI is defined in the file: <docker-compose.yml>. 
The dbaas Flask application listens on port 5000 using the uWSGI protocol.

### Prodution and Development
Production and development instance run on seperate systems. The differances between production and development effect the Nginx web interface and not the application code.  Nginx configurations are defined in two subdirectories <prod> and <dev>.  The environment variable DBAAS_ENV most be set to either <prod> or <dev> for docker build to work.

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
All differences between produciton and development for DBaas are contained in the config.py file. Two version of config.py are maintained in git; <config.prod.py> and <config.dev.py>.  confi.py is ignored by git.  After cloning the git repo either the prod or the dev file needs to be copied to create config.py

```bash
cp config.dev.py config.py
cp postgresdb/config.dev.py postgresdb/config.py
# OR
cp config.prod.py config.py
cp postgresdb/config.prod.py postgresdb/config.py
```

### Postgres Container Management 
The need to support multible different version of Postgres will require support mulitpile Docker 
images for PostgresdB.  The config for choosing the image has been moved into the postgresdb/config.py. 

```python
# List of Postgres Docker Images
# list of lists, First element is the Label, second element is the name of the image
# First item in list is the Default
postgres_images = [['Postgres 9.5', 'postgres:9.5.3'],
                   ['Posrgres 9.4', 'postgres:9.4.10'],
]
```

create container
add container to Container table
  Create action logged
add entry to state table

Delete Container
  log deletion
  remove from state table

Restart Container
  log restart

Postgres Create
  longpass
  create_con( params, env)
  Add Longpass to Admin DB by hand,
