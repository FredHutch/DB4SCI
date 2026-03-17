#!/bin/bash
set -e

# Start cron in the background
echo "Starting cron daemon..."
cron

# Load AWS credentials from Docker secrets
# export AWS_ACCESS_KEY_ID=$(cat /run/secrets/aws_access_key_id)
# export AWS_SECRET_ACCESS_KEY=$(cat /run/secrets/aws_secret_access_key)
# export AWS_BUCKET_NAME=$(cat /run/secrets/aws_bucket_name)
export AWS_DEFAULT_REGION=us-west-2  # or whatever region you use

# Pass environment variables to cron jobs
printenv | grep -v "no_proxy" > /etc/environment

# Wait for admin database to come up
# TODO FIXME do not hardcode hostnames and port numbers
./wait-for-it.sh admin_db:5432 -- echo "(entrypoint) admin_db is up"
./wait-for-it.sh migrate_db:5432 -- echo "(entrypoint) migrate_db is up"


# Execute the main command (Flask app)
echo "Starting Flask application..."
exec "$@"
