#!/usr/bin/env python

import os
import boto3
from mydb.config import Config

def main():
    "do the work"
    session = boto3.Session()
    credentials = session.get_credentials()
    credentials = credentials.get_frozen_credentials()
    access_key = credentials.access_key
    secret_key = credentials.secret_key
    region = session.region_name

    print("export AWS_ACCESS_KEY_ID={}".format(access_key))
    print("export AWS_SECRET_ACCESS_KEY={}".format(secret_key))
    print("export AWS_DEFAULT_REGION={}".format(region))
    print("export AWS_BUCKET={}".format(Config.bucket))

if __name__ == "__main__":
    main()
