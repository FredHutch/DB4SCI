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

echo "Install OS packages"
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

echo "Install Python packages"
pip install --upgrade pip
pip install -r /opt/DB4SCI/requirements.txt

echo 'check for Docker'
docker_path=$(which docker)
if [ -x "$docker_path" ] ; then
    echo " -- Docker Installed"
    docker_ver=(`${docker_path} --version`)
    ver=${docker_ver[2]}
    if [[ $ver == "18."* ]]; then
        echo "Docker version ${ver} is good"
    else
        echo "Don't like your Docker version.  Did you install Docker CE?"
        exit 1
    fi
else
    echo "Can't find Docker. I'll install it for you."
    echo "Using Docker get-docker install script"
    ${basedir}/get-docker.sh
    echo "Install docker-compose"
    curl -L "https://github.com/docker/compose/releases/download/1.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
fi

echo 'check for docker-compose'
compose_ver=`docker-compose --version`
if [[ $? -ne 0 ]]; then
    echo 'Is docker-compose installed?'
    exit 1
fi

echo 'Pull Docker database images'
docker pull ubuntu:16.04@sha256:1dfb94f13f5c181756b2ed7f174825029aca902c78d0490590b1aaa203abc052
# docker pull ubuntu:18.04@sha256:017eef0b616011647b269b5c65826e2e2ebddbe5d1f8c1e56b3599fb14fabec8
docker pull mariadb:10.3.11@sha256:12e32f8d1e8958cd076660bc22d19aa74f2da63f286e100fb58d41b740c57006
docker pull mariadb:10.4@sha256:e7490991d0919097ed671700d41425047fd3c2329c69cbc517c3c1c60ffd3515
docker pull postgres:10.7@sha256:3a397af7ca5b55994a7635f0a9ca6126ef5f8bb0bb5e21d3e6ed267399601238
docker pull postgres:9.6.12@sha256:78890d2b9c6a8eb312b1c4f4ee460da1d1d16d27f94312b910fbf43a30230ba4
docker pull mongo:4.1.5@sha256:cf0e229c2b615d9d4bd46e74140e49a0b86a1e31ac602780730ccb475c69b6e6
docker pull nginx:1.13.8@sha256:0ffc09487404ea43807a1fd9e33d9e924d2c8b48a7b7897e4d1231a396052ff9

# Setup Environment 
# In production mode the script env_setup.sh is used to setup the environment.
# cp env_setup.demo env_setup.sh 
# edit env_setup.sh 
# source ./env_setup.sh prod
export AWS_ACCESS_KEY_ID=aws-access-key-id
export AWS_SECRET_ACCESS_KEY=aws-secret-access-key

export DB4SCI_HOST=localhost
export DB4SCI_MOD=demo
export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_HOST}:32009/mydb_admin"
export AWS_BUCKET="s3://your-aws-bucker/prod"
export SSL_CERTS="/opt/DB4SCI/ssl"
export DEMO=1

cd /opt/DB4SCI
if [[ ! -f /opt/DB4SCI/mydb/conif.py ]]; then
    echo Copy Config from example
    cp mydb/config.example mydb/config.py
fi

echo "Start the Flask App..."
./webgui.py
