#!/bin/bash
#
# install_demo.sh
#
# DB4SCI bootstrap script
#
# Demo Mode 
# install DB4SCI on a personal computer for demo purposes. TSL and authentication
# are not configured. Requires local install of Docker CE >17.0
# Does not use uwsgi nor Nginx. Note for use in a produciton environment!

# check for docker
echo 'check Docker'
docker_ver=`docker --version`
if [[ $? -ne 0 ]]; then
    echo 'Is Docker installed?'
    exit 1
fi
ver=($docker_ver)
if [[ ${ver[2]} == "17."* || ${ver[2]} == "18."* ]]; then
    echo "Docker version ${ver[2]} is good"
else
    echo "Don't like your Docker version.  Did you install Docker CE?"
    exit 1
fi

# This is OSX issue, localhost can not be used by Docker on OSX.
echo Create extra loopback port for Docker: 172.16.123.1
echo sudo is required
sudo ifconfig lo0 alias 172.16.123.1

echo 'Create directories'
basedir=/private/mydb/
GID=`id | sed 's/^.*gid=\([0-9]*\).*$/\1/'`
sudo mkdir -p ${basedir}
sudo chown $USER:$GID ${basedir}
chmod g+w ${basedir}
mkdir -p ${basedir}{repos,db_backups,db_data,logs}
mkdir -p ${basedir}{uwsgi,nginx}
cd ${basedir}repos

echo 'Cloning DB4SCI '
git clone https://github.com/FredHutch/DB4SCI.git
# use curl do download rlease 
# unzip
cd ${basedir}repos/DB4SCI

echo 'Pull Docker database images'
docker pull ubuntu:16.04@sha256:1dfb94f13f5c181756b2ed7f174825029aca902c78d0490590b1aaa203abc052
docker pull mariadb:10.3sha256:3792912862b389e10831b27cda0feb5d42363b30002ea8f56e35ff8a2af02df2
docker pull postgres:10.3@sha256:1c2cc88d0573332ff1584f72f0cf066b1db764166786d85f5541b3fc1e362aee
docker pull postgres:9.6.8sha256:2b70c00c8d3b8d5ed07c6d84d4d8b5cefd148d8e855d813a4ec05571b509c301
docker pull mongo:3.4.1@sha256:aff0c497cff4f116583b99b21775a8844a17bcf5c69f7f3f6028013bf0d6c00c
#docker pull neo4j:3.2.5
#docker pull nginx:1.13.8

# Setup Environment 
# In production mode the script env_setup.sh is used to setup the environment.
# cp env_setup.demo env_setup.sh 
# edit env_setup.sh 
# source ./env_setup.sh prod
export AWS_ACCESS_KEY_ID=aws-access-key-id
export AWS_SECRET_ACCESS_KEY=aws-secret-access-key
DB4SCI_HOST=localhost
export DBAAS_ENV=prod
export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_HOST}:32009/mydb_admin"
export AWS_BUCKET="s3://your-aws-bucker/prod"
export SSL_CERTS="/opt/dbaas/ssl"
export DEMO=1

cp mydb/local_config.example mydb/local_config.py

echo "Building DB4SCI container..."
cd /mydb/repos/DB4SCI
docker build --tag demo:1.0 --file Dockerfile.demo  .

echo "Starting DB4SCI"
echo "Browse to 172.16.123.1"
docker run \
 --name demo \
 --publish 172.16.123.1:80:5000/tcp \
 -v /var/run/docker.sock:/var/run/docker.sock \
 --volume /private/mydb/db_data:/mydb/db_data \
 --volume /private/mydb/db_backups:/mydb/db_backups \
 --volume /private/mydb/mariadb_keys:/mydb/mariadb_keys \
 --volume /private/mydb/logs:/mydb/logs \
 -e DEMO=1 \
 -e DBAAS_ENV=${DBAAS_ENV} \
 -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
 -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
 -e SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI} \
 -e TZ=America/Los_Angeles \
 --label DBaaS=true \
 demo:1.0
