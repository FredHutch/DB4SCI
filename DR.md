# DB4Sci Disaster Recovery

What to do if your local on-premises server is dead.

#### Recreate DB4Sci from scratch

 * Find a new server or spin up an EC2 instace. Start with a fresh install of
Ubuntu 16.04.
 * Start your EC2 instance with the same account as your S3 bucket that
   your database backups. 
 * Install Docker CE version 18.X and docker-compose
   [https://docs.docker.com/install/linux/docker-ce/ubuntu/](How to install Docker CE for Ubuntu)
 * Install DB4sci by running the demo startup script from https://DB4Sci.org
 * Copy your protected copies of configure files from your secrets repository
 ** mydb/config.py
 ** prod/ngix/ssl
 ** .aws/creditals
 ** .aws/config
 ** build_run.sh
 ** Dockerfile
 ** docker-compose
 * re-run the script `build_run.py prod`.

At this point you will have a fresh install of DB4Sci with an empty admin
database. The next step is to recover your `mydb_admin` database. Create
a new PostgreSQL container with a new name like: DR_admin. Follow the
Postgres restore instructions to recover the DB. The mydb_admin database
table `container_state` has a list of running databases that need to
restored.
