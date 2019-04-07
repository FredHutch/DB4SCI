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
    ip = os.environ.get('DB4SCI_IP')
    if level is None:
        print("DB4SCI_MODE environemnt must be set to ['prod'|'dev'|'demo']")
        sys.exit(1)
    if level == 'prod':
        app.logger.setLevel(logging.INFO)
        app.run(threaded=True, debug=False)
    elif level == 'demo':
        print("Demo Staring URL: http://{ip}:5000/".format(ip=ip))
        app.logger.setLevel(logging.DEBUG)
        app.run(host=ip, threaded=True, debug=True)
