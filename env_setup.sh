#!/bin/bash
#
# setup environment for Flask
# DB4SCI_MODE must be set before docker-compose is run

if [ -z "$1" ]; then
   echo Usage:  ['prod', 'demo']
   exit 1
fi

export DB4SCI_MODE=$1
export DB4SCI_HOST=`uname -n`
export DB4SCI_IP=`ip route get 8.8.8.8 | head -1 | sed 's/^.*src \([0-9\.]*\).*/\1/'`
export DB4SCI_CERTS="/opt/DB4SCI/ssl"

# set AWS creds as environment variaables
if [[ -f .aws/config ]]; then
`./read_aws_credentials.py`
fi

case $DB4SCI_MODE in
    "prod")
        ;;
    "demo")
        ;;
    "dev")
        export AWS_BUCKET=${AWS_BUCKET}/dev
        ;;
    *)
        echo DB4SCI_MODE must be set
        exit 1
        ;;
esac

export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_HOST}:32009/mydb_admin"
