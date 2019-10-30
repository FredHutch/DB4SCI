#!/bin/bash
#
# setup environment for Flask
# DB4SCI_MODE must be set before docker-compose is run

if [ -z "$1" ]; then
   echo Usage:  ['prod', 'dev', 'test', 'demo']
   exit 1
fi

export DB4SCI_MODE=$1

case $DB4SCI_MODE in
"prod")
    export DB4SCI_HOST=`uname -n`
    export AWS_BUCKET="s3://your-aws-bucket/prod"
    export SSL_CERTS="/opt/dbaas/ssl"
    ;;
"dev")
    ;;
"test")
    ;;
"demo")
    export DB4SCI_HOST='0.0.0.0'
    export AWS_BUCKET="s3://your-bucket-name/prod"
    export SSL_CERTS="/opt/dbaas/ssl"
    export MYDB_ROOT=/private/mydb/
    ;;
*)
    echo DB4SCI_MODE must be set
    exit 1
    ;;
esac

# set AWS creds as environment variaables
if [[ -f .aws/config ]]; then
`./read_aws_credentials.py`
fi

export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_HOST}:32009/mydb_admin"
