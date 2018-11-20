#!/bin/bash
#
# setup environment for Flask
# DBAAS_ENV must be set before docker-compose is run

if [ -z "$1" ]; then
   echo Usage:  ['prod', 'dev', 'test', 'demo']
   exit 1
fi

export DBAAS_ENV=$1

#  Configure AWS Keys
export AWS_ACCESS_KEY_ID=AKIAJDS42RAFEQYAZDZA
export AWS_SECRET_ACCESS_KEY=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
export AWS_BUCKET="s3://fh-div-adm-scicomp-mydb-backup/prod"

# Configure Hostname (do not use localhost)
export HOST_IP=172.17.64.143
export HOSTNAME=db4sci-dev.fhcrc.org

export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${HOSTNAME}:32009/mydb_admin"
export SSL_CERTS="/opt/dbaas/ssl"

case $DBAAS_ENV in
"prod")
    ;;
"dev")
    export AWS_BUCKET="s3://fh-div-adm-scicomp-mydb-backup/dev"
    ;;
"test")
    ;;
"demo")
    export SSL_CERTS="/opt/dbaas/ssl"
    ;;
*)
    echo DBAAS_ENV must be set
    exit 1
    ;;
esac

echo Build Containers
docker-compose build

echo Start dbaas
docker-compose up -d 
