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

if [[ `uname -s` = "Linux" ]]; then
   echo "-- Linux detected"
else
   echo "DB4Sci Demo only works with Linux"
   exit 1
fi
if [[ -f /etc/os-release ]]; then
   . /etc/os-release
   if [[ ${NAME} = "Ubuntu" ]]; then
       echo "-- Ubuntu detected"
   else
       echo "DB4Sci has only been tested with Ubuntu"
       exit 1
   fi
else
    echo "/etc/os-release not found. Please install Ubuntu"
    exit 1
fi

echo 'Checking for Docker'
docker_path=$(which docker)
if [[ -s ${docker_path} ]] && [[ -x ${docker_path} ]] ; then
    echo " -- Docker Installed"
else
    echo "Can't find Docker. Is it installed?"
    echo "Please follow these instructsions to install Docker CE"
    echo "and install docker-compose. Be sure the docker daemon is up."
    echo "daemon: systemctl status docker"
    echo "https://docs.docker.com/install/linux/docker-ce/ubuntu/"
    echo "https://docs.docker.com/compose/install/"
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

echo 'Checking for docker-compose'
docker_path=$(which docker-compose)
if [[ -s $docker_path} ]] && [[ -x ${docker_path} ]]; then
    compose_ver=`docker-compose --version`
    if [[ $? -ne 0 ]]; then
        echo 'Is docker-compose installed?'
        exit 1
    fi
else
    echo " -- docker-compose detected"
fi


echo 'Checking for DB4Sci git clone'
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
docker pull mariadb:10.3@sha256:3792912862b389e10831b27cda0feb5d42363b30002ea8f56e35ff8a2af02df2
docker pull postgres:10.5@sha256:e19acdab213d6318565a6da5fb824ca5161e99fe63dbc37036557aacb35fae51
docker pull postgres:9.6.10@sha256:228b67b16c15ca470e0a9ecd52a7e3821bf9efca2ab631ca287f727fceee27ab
docker pull mongo:3.4.1@sha256:aff0c497cff4f116583b99b21775a8844a17bcf5c69f7f3f6028013bf0d6c00c
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

