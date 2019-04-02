#!/usr/bin/python
import os
import sys
import logging
from mydb import app
from mydb.mydb_setup import mydb_setup

"""Flask start script for DB4SCI 
"""

mydb_setup()

if __name__ == "__main__":
    level = os.environ.get('DB4SCI_MODE')
    if level is None:
        print("DB4SCI_MODE environemnt must be set to ['prod'|'dev'|'test'|'demo']")
        sys.exit(1)

    if level == 'prod':
        app.logger.setLevel(logging.INFO)
        app.run(threaded=True, debug=False)
    elif level == 'demo':
        app.logger.setLevel(logging.DEBUG)
        app.run(host='0.0.0.0',threaded=True,debug=True)
