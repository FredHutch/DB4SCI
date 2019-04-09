#!/bin/bash
#
# install_demo.sh
#
# DB4SCI bootstrap script
#
# Demo Mode 
# install DB4SCI for demo purposes. TSL and authentication
# are not configured.
#
#  John Dey jfdey@fredhutch.org
#  Oct 2018
#  Apr 2019 - rewrite for local demo mode

set -e

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

echo "-- Create docker user"
if [[ stat=`groupadd -f --gid 999 docker` ]]; then
    echo group docker exists
fi
if [[ stat=`useradd -u 999 -g 999 -m -s /bin/nologin docker` ]]; then
    echo user docker exists
fi

echo "-- Create SourceDir"
basedir=/opt/DB4SCI
if [[ ! -d ${basedir} ]]; then
    mkdir -p ${basedir}
    chown 999:999 ${basedir}
fi

echo "-- Check for DB4Sci clone"
if [[ ! -d '/opt/DB4SCI/.git' ]]; then
    echo "-- Cloning DB4Sci"
    cd /opt
    su -s /bin/bash docker -c "git clone https://github.com/FredHutch/DB4SCI.git"
fi

echo "-- Create directories"
mkdir -p ${basedir}/admin_db
mkdir -p ${basedir}/admin_db/{data,backup}
chown -R 999:999 ${basedir}/admin_db

mkdir -p /mydb/{db_data,db_backups,logs}
mkdir -p /mydb/logs/{uwsgi,nginx}
chown -R 999:999 /mydb

echo "-- Install OS packages"
apt-get -y -qq update && apt-get -y -qq install \
    python \
    python-dev \
    python-pip \
    postgresql-server-dev-all \
    libldap2-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    libffi-dev \
    postgresql-client \
    libmysqlclient-dev \
    mariadb-client \
    apt-transport-https \
    ca-certificates \
    uwsgi \
    uwsgi-core \
    uwsgi-plugin-python \
    curl \
    software-properties-common

# pip install --quiet --upgrade pip
echo "-- Install Python packages"
pip2 install -q -r /opt/DB4SCI/requirements.txt

echo "-- Checking for Docker"
if [[ -x "$(command -v docker)" ]]; then
    echo "-- Docker Installed"
    docker_ver=(`docker --version`)
    ver=${docker_ver[2]}
    if [[ $ver == "18."* ]]; then
        echo "-- Docker version ${ver} is good"
    else
        echo "Don't like your Docker version.  Did you install Docker CE?"
        exit 1
    fi
else
    echo "-- Can't find Docker. I'll install it for you."
    echo "-- Using Docker get-docker install script"
    /bin/bash ${basedir}/get-docker.sh
fi

echo "-- Check for docker-compose"
if [[ -x "$(command -v docker-compose)" ]]; then
    echo "-- Docker-compose is installed"
else
    echo "-- Installing docker-compose"
    curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
fi

echo "-- Pull Docker database images"
docker pull ubuntu:16.04
# docker pull ubuntu:18.04
docker pull mariadb:10.4
docker pull postgres:9.6.12
docker pull postgres:10.7
docker pull mongo:4.1.9
docker pull nginx:1.15.10

echo "-- Generate Selfsigned TLS Certs (https)"
sudo -u docker /opt/DB4SCI/TLS/TLS-create.sh

# In production mode the script env_setup.sh is used to setup the environment.
# edit env_setup.sh
# source ./env_setup.sh prod
sudo -u docker bash <<EOF
cd /opt/DB4SCI

echo "-- Setup Environment"
export AWS_ACCESS_KEY_ID=aws-access-key-id
export AWS_SECRET_ACCESS_KEY=aws-secret-access-key
export DB4SCI_HOST=localhost
export DB4SCI_IP=`ip route get 8.8.8.8 | head -1 | sed 's/^.*src \([0-9\.]*\).*/\1/'`
export DB4SCI_MODE=demo
export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_IP}:32009/mydb_admin"
export AWS_BUCKET="s3://your-aws-bucker/prod"
export DB4SCI_CERTS="/opt/DB4SCI/ssl"

if [[ ! -f /opt/DB4SCI/mydb/conif.py ]]; then
    echo "-- Copy Config from example"
    cp mydb/config.example mydb/config.py
fi

echo "-- Start the Flask App..."
exec python /opt/DB4SCI/webui.py
EOF