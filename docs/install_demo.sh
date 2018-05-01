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
basedir=/private/mydb
mkdir -p /private/mydb/{repos,db_backups,db_data,logs}
mkdir -p /private/mydb/logs/{uwsgi,nginx}
cd /private/mydb/repos

echo 'Cloning DB4SCI '
git clone https://github.com/FredHutch/DB4SCI.git
# use curl do download rlease 
# unzip

echo 'Pull Docker database images'
docker pull ubuntu:16.04
docker pull mariadb:10.3
docker pull postgres:10.3
docker pull postgres:9.6.8
docker pull mongo:3.4.1
#docker pull neo4j:3.2.5
#docker pull nginx:1.13.8

# Setup Environment 
source ./env_setup.demo prod
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
 -e DBAAS_ENV=${DBAAS_ENV} \
 -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
 -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
 -e SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI} \
 -e TZ=America/Los_Angeles \
 --label DBaaS=true \
 demo:1.0
