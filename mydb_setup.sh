#!/bin/bash
set -e

# This might be needed is your are using Zfs
#echo "Installing docker systemd service config..."
#cp docker.service /lib/systemd/system/docker.service
#systemctl restart docker

echo "Install backup cron..."
cp mydb_backup.crontab /etc/cron.d/mydb_backup

echo "Send Flask logs to Syslog"
cp 60-mydb.conf /etc/rsyslog.d/
systemctl restart rsyslog

echo "setup log rotation"
cp dbaas.logrotate /etc/logrotate.d/dbaas
