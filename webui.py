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
    if level is None:
        print("DBAAS_ENV environemnt must be set to ['prod'|'dev'|'test'|'demo']")
        sys.exit(1)

    if level == 'prod' or level == 'demo':
        app.logger.setLevel(logging.DEBUG)
        app.run(threaded=True, debug=False)
    elif level == 'dev':
        app.logger.setLevel(logging.DEBUG)
        app.run(threaded=True,debug=True)
