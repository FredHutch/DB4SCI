#!/bin/bash
#
# install.sh
#
# DB4SCI bootstrap script
#

# check for docker
echo 'check Docker'
docker_ver=`docker --version`
if [[ $? -ne 0 ]]; then
    echo 'Is Docker installed?'
    exit 1
fi
compose=`docker-compose --version`
if [[ $? -ne 0 ]]; then
    echo 'Is Docker Compose installed?'
    exit 1
fi
ver=($docker_ver)
if [[ ${ver[2]} == "17."* || ${ver[2]} == "18."* ]]; then
    echo "Docker version ${ver[2]} is good"
else
    echo "Don't like your Docker version.  Did you install CE?"
    exit 1
fi

echo 'check docker-compose'
ver=($compose)
if [[ ${ver[2]} == "1.17."* || ${ver[2]} == "1.18."* ]]; then
    echo "Docker Compose ${ver[2]} is good"
else
    echo "Don't like the Docker Compose version. 1.17 > is required"
    exit 1
fi

# create extra loopback port
sudo ifconfig lo0 alias 172.16.123.1

# Create working area
echo 'Create directories'
mkdir -p /mydb/{repos,db_backups,db_data,logs}
cd /mydb/repos

echo 'Clone DB4SCI'
git clone https://github.com/FredHutch/DB4SCI.git
# use curl do download rlease 
# unzip

echo 'docker pull images'
docker pull ubuntu:16.04
docker pull mariadb:10.3
docker pull postgres:10.3
docker pull postgres:9.6.8
docker pull mongo:3.4.1
docker pull neo4j:3.2.5
docker pull nginx:1.13.8

# Setup Environment 
cp env_setup.example env_setup.sh
cp prod/nginx/demo.conf prod/nginx/mydb.conf
source ./env_setup.sh prod

echo "Building DB4SCI container..."
cd /mydb/repos/DB4SCI
docker build
docker run -p 80:80 \
 -d \
 --name dbaas \
 -v /mydb/db_data:/mydb/db_data \
 -v /mydb/logs:/mydb/logs \
 -v /var/run/docker.sock:/var/run/docker.sock \
 -v /mydb/db_backups:/mydb/db_backups \
 -e DBAAS_ENV=${DBAAS_ENV} \
 -e "TZ=America/Los_Angeles" \
 -e SQLALCHEMY_DATABASE_URI=${SQLALCHEMY_DATABASE_URI} \
 dbaas:1.7.0


