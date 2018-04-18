#!/usr/bin/env python
from human_uptime import human_uptime 

"""Test human_uptime from container_util
to make this code better test data should be generated dynamicly
so all test cases are exercised.

data:  less than 30 seconds 
       less than 1 minutue
       less than 1 hour
       less than 1 day
       less than one week
       less than one month
       less than one year 
   etc...
"""

if __name__ == "__main__":
    timestamps = ["2017-03-14T20:40:41.605600023Z",
                 "2017-02-16T20:40:41.605600023Z",
                 "2017-03-03T20:40:41.605600023Z",
                 "2017-03-07T20:40:41.605600023Z",
                 "2017-03-14T04:44:09.976331599Z"]
    for ts in timestamps:
        print("TS: %s  Human: %s" % (ts, human_uptime(ts)))
