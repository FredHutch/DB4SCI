#!/bin/bash
#
# setup environment for Flask
# DB4SCI_MODE must be set before docker-compose is run

if [ -z "$1" ]; then
   echo Usage:  ['prod', 'demo']
   exit 1
fi

DB4SCI_HOME=/opt/DB4SCI
export DB4SCI_MODE=$1
export DB4SCI_HOST=`uname -n`
export DB4SCI_IP=`ip route get 8.8.8.8 | head -1 | sed 's/^.*src \([0-9\.]*\).*/\1/'`
export DB4SCI_CERTS="/opt/DB4SCI/ssl"

# set AWS creds as environment variaables
if [[ -f ${DB4SCI_HOME}/.aws/config ]]; then
`./read_aws_credentials.py`
else
    echo "-- AWS credentials not configured"
    export AWS_ACCESS_KEY_ID=aws-access-key-id
    export AWS_SECRET_ACCESS_KEY=aws-secret-access-key
    export AWS_BUCKET="s3://your-aws-bucker/prod"
fi

if [[ ! -f /opt/DB4SCI/mydb/conif.py ]]; then
    echo "-- Copy Config from example"
    cp ${DB4SCI_HOME}/mydb/config.example ${DB4SCI_HOME}/mydb/config.py
fi

export SQLALCHEMY_DATABASE_URI="postgresql://mydbadmin:db4docker@${DB4SCI_IP}:32009/mydb_admin"
case $DB4SCI_MODE in
    "prod")
        # docker compose
        ;;
    "demo")
        export DB4SCI_HOST=${DB4SCI_IP}
        echo "-- Start the Flask App..."
        exec python ${DB4SCI_HOME}/webui.py
        ;;
    "dev")
        export AWS_BUCKET=${AWS_BUCKET}/dev
        ;;
    *)
        echo DB4SCI_MODE must be set
        exit 1
        ;;
esac




