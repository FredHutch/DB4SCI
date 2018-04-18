#!/bin/bash
#
# install.sh
#
# DB4SCI bootstrap script
#

if [[ ! -d /mydb ]]; then
    mkdir -p /mydb/repo
    cd /mydb/repo
fi
git clone https://github.com/FredHutch/DB4SCI.git

# test for docker
docker pull 
