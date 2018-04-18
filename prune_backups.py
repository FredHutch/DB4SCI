#!/usr/bin/python

import os
import sys
import time
from subprocess import call
import mydb.config as config

now = time.time()
cutoff = now - (2 * 86400)

for root, dirs, files in os.walk(config.var.backupvol): 
    for name in files:
        full = os.path.join(root, name)
        t = os.stat(full)
        c = t.st_ctime
        if c < cutoff:
            print("prune: %s" % full) 
            os.remove(full)
