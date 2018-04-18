# OS Setup for mydb.fhcrc.org
## Manual Steps

* Install 16.04 onto OS SSD with hostname "mydb.fhcrc.org" and point "mydb.fredhutch.org" CNAME to it
* Configure ethernet bonding (was unable to test this in virtual/container env) /etc/network/interfaces.d/70-bond0.cfg:
```
auto <1st interface name>
iface <1st interface name> inet manual
bond-master bond0
bond-primary eth1

auto <2nd interface name>
iface <2nd interface name> inet manual
bond-master bond0

auto bond0
iface bond0 inet dhcp
bond-mode balance-alb
bond-slaves <1st interface name> <2nd interface name>
bond-miimon 100
```
* Install chef package and bootstrap
* Disable logins for all but SciComp
* Install ZFS and configure NVMe drives as a zpool at /mydb
* Add a ZFS mounted at /var/lib/docker
```
apt-get install zfsutils-linux
zpool create mydb <NVMe device> <NVMe device>
zfs create -o mountpoint /var/lib/docker mydb/docker
zfs create mydb/postgres_dbs
zfs create mydb/db_backups
zfs create mydb/repos
```
## Automated steps - see mydb.setup.sh in this repo
* Add the Docker repo key
```
apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
```
* Add the Docker APT repo
```
apt-add-repository "deb https://apt.dockerproject.org/repo ubuntu-xenial main"
```
* Run apt-get update
```
apt-get update
```
* Install packages
```
apt-get install docker-engine git awscli
apt-get install libpq-dev
apt-get install libmysqlclient-dev
pip install psycopg2
pip install ldap3
pip install MySQL-python
```
* Install docker compose
```
curl -L https://github.com/docker/compose/releases/download/1.8.0-rc1/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```
* Clone repos for management container (you will need to log into github as a user that has permissions)
```
cd /mydb/repos
git clone https://github.com/FredHutch/DB4SCI.git
```
* Copy docker.service from git repo to /etc/systemd/system/docker.service
```
cp /mydb/repos/postgres_container_mgmt/docker.service /etc/systemd/system/docker.service
```
For DEV, remove `--storage-driver=zfs` from the docker.service file or it will not work on VM/LXC.
* Start docker engine service
```
systemctl restart docker
```
* Deploy and/or update the UI/mgmt container
```
cd /mydb/repos/postgres_container_mgmt
git pull
docker-compose build
docker-compose up
```
* Configure nagios (install agent?)
* Install cron for backups
* Create pgpass file to access pgjson administrative database.
```
cp /mydb/repos/postgres_container_mgmt/mydb_backup.crontab /etc/cron.d/mydb_backup
echo 'mydb:32010:pgjson:pgjson:db4docker' >/root/.pgpass
chmod 600 /root/.pgpass
```
* Yay!
