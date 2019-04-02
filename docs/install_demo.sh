#!/bin/bash
#
# install_demo.sh
#
# DB4SCI bootstrap script
#
# Demo Mode 
# install DB4SCI for demo purposes. TSL and authentication
# are not configured. Requires local install of Docker CE >18.0
#
#  John Dey jfdey@fredhutch.org
#  Oct 2018

set -e -x

if [[ `uname -s` = "Linux" ]]; then
   echo "-- Linux Detected"
else
   echo "DB4Sci Demo only works with Linux"
   exit 1
fi
if [[ -f /etc/os-release ]]; then
   . /etc/os-release
   if [[ ${NAME} = "Ubuntu" ]]; then
       echo "-- Ubuntu Detected"
   else
       echo "DB4Sci has only been tested with Ubuntu"
       exit 1
   fi
else
    echo "/etc/os-release not found. Please install Ubuntu"
    exit 1
fi

echo 'check for Docker'
docker_path=$(which docker)
if [ -x "$docker_path" ] ; then
    echo " -- Docker Installed"
else
    echo "Can't find Docker. Is it installed?"
    echo "Please follow these instructsions to install Docker CE"
    echo "https://docs.docker.com/install/linux/docker-ce/ubuntu/"
    exit 1
fi

docker_ver=`${docker_path} --version`
ver=($docker_ver)
if [[ ${ver[2]} == "18."* || ${ver[2]} == "18."* ]]; then
    echo "Docker version ${ver[2]} is good"
else
    echo "Don't like your Docker version.  Did you install Docker CE?"
    exit 1
fi

echo 'check for docker-compose'
compose_ver=`docker-compose --version`
if [[ $? -ne 0 ]]; then
    echo 'Is docker-compose installed?'
    exit 1
fi


echo 'Check for DB4Sci clone'
if [[ ! -d '/opt/DB4SCI/.git' ]]; then
    echo ' - Cloning DB4Sci'
    cd /opt
    git clone https://github.com/FredHutch/DB4SCI.git
fi

echo 'Create directories'
basedir=/opt/DB4SCI
sudo mkdir -p ${basedir}
mkdir -p ${basedir}{backup,data,logs}
mkdir -p ${basedir}{uwsgi,nginx}
sudo mkdir -p /var/log/uwsgi

echo 'Pull Docker database images'
docker pull ubuntu:16.04@sha256:1dfb94f13f5c181756b2ed7f174825029aca902c78d0490590b1aaa203abc052
docker pull mariadb:10.3.11@sha256:12e32f8d1e8958cd076660bc22d19aa74f2da63f286e100fb58d41b740c57006
docker puall mariad:10.4@sha256:e7490991d0919097ed671700d41425047fd3c2329c69cbc517c3c1c60ffd3515
docker pull postgres:10.7@sha256:3a397af7ca5b55994a7635f0a9ca6126ef5f8bb0bb5e21d3e6ed267399601238
docker pull postgres:9.6.10@sha256:228b67b16c15ca470e0a9ecd52a7e3821bf9efca2ab631ca287f727fceee27ab
docker pull mongo:4.1.5@sha256:cf0e229c2b615d9d4bd46e74140e49a0b86a1e31ac602780730ccb475c69b6e6
#docker pull neo4j:3.2.5
docker pull nginx:1.13.8@sha256:0ffc09487404ea43807a1fd9e33d9e924d2c8b48a7b7897e4d1231a396052ff9

# Setup Environment 
# In production mode the script env_setup.sh is used to setup the environment.
# cp env_setup.demo env_setup.sh 
# edit env_setup.sh 
# source ./env_setup.sh prod
export AWS_ACCESS_KEY_ID=aws-access-key-id
export AWS_SECRET_ACCESS_KEY=aws-secret-access-key
export HOSTNAME=`host -TtA $(uname -n) | awk '{print $1}'`
export HOST_IP=`ip route get 8.8.8.8 | awk 'NR==1 {print $NF}'`
DB4SCI_HOST=localhost
export MYDB_ROOT=/mydb
export DBAAS_ENV=demo
export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_HOST}:32009/mydb_admin"
export AWS_BUCKET="s3://your-aws-bucker/prod"
export SSL_CERTS="/opt/dbaas/ssl"
export DEMO=1

cd /opt/DB4SCI
if [[ ! -f /opt/DB4SCI/mydb/conif.py ]]; then
    echo Copy Config from example
    cp mydb/config.example mydb/config.py
fi

echo "Building DB4SCI container..."
docker-compose build 
docker-compose up -d

