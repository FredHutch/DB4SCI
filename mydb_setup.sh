#!/bin/bash
set -e

# setup script for mydb project
BASE=/mydb

# assume the following exist (and are zfs filesystems)
#
#   /var/lib/docker
#   /mydb/repos
#   /mydb/postgres_dbs
#   /mydb/db_backups

echo "Adding Docker repo ..."
apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
apt-add-repository "deb https://apt.dockerproject.org/repo ubuntu-xenial main"

echo "Installing packages..."
apt-get update
apt-get install docker-engine git awscli

echo "Installing docker compose..."
curl -L https://github.com/docker/compose/releases/download/1.19.0/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

echo "Cloning repos..."
cd /mydb/repos
git clone https://github.com/FredHutch/postgres_container_mgmt.git
git clone https://github.com/FredHutch/postgres_docker_95.git

echo "Installing docker systemd service config..."
cp /mydb/repos/postgres_container_mgmt/docker.service /etc/systemd/system/docker.service
systemctl restart docker

# down load docker images
docker pull ubuntu:16.04@sha256:7a64bc9c8843b0a8c8b8a7e4715b7615e4e1b0d8ca3c7e7a76ec8250899c397a
docker pull mariadb:10.3sha256:26614427d1830bbcbd5995982048ed30bafcd7060b5622d48d728a4438ac48a1
docker pull postgres:10.3@sha256:e2688f79c920bbd5bcb8e1ed54aef522c7e93a1a5eab32e10b4b020d49b4b925
docker pull postgres:9.6.1
docker pull mongo:3.4.1
docker pull neo4j:3.2.5
docker pull nginx:1.13.8

echo "Deploying postgres_container_mgmt..."
cd /mydb/repos/postgres_container_mgmt
/usr/local/bin/docker-compose build

echo "Install backup cron..."
cp /mydb/repos/postgres_container_mgmt/mydb_backup.crontab /etc/cron.d/mydb_backup

echo "Send Flask logs to Syslog"
cp /mydb/repos/postgres_container_mgmt/60-mydb.conf /etc/rsyslog.d/
systemctl restart rsyslog

echo "setup log rotation"
cp /mydb/repos/postgres_container_mgmt/dbaas.logrotate /etc/logrotate.d/dbaas

echo "create directories for logs and configuration data"
mkdir -p ${BASE}/log/nginx
mkdir -p ${BASE}/log/uwsgi
mkdir ${BASE}/mariadb_keys
