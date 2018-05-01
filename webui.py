#!/usr/bin/python
import os
import sys
import logging
from mydb import app
from mydb.mydb_setup import mydb_setup

"""Flask start script for MYDB DBAAS
"""

mydb_setup()

if __name__ == "__main__":
    level = os.environ.get('DBAAS_ENV')
    demo = os.environ.get('DEMO')
    if level is None:
        print("DBAAS_ENV environemnt must be set to ['prod'|'dev'|'test']")
        sys.exit(1)
   
    if demo:
        print("starting in demo mode")
        app.run(host="172.16.123.1", threaded=True, debug=True)

    if level == 'prod':
        app.logger.setLevel(logging.DEBUG)
        app.run(threaded=True, debug=False)
    elif level == 'dev':
        app.logger.setLevel(logging.DEBUG)
        app.run(threaded=True,debug=True)
