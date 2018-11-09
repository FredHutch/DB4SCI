#!/usr/bin/env python

from argparse import ArgumentParser
import admin_db

from config import Config

"""Test admin_db fucntions.
"""
(header, body) = admin_db.display_container_state()
print(header)
print(body)

(header, body) = admin_db.display_active_containers()
print(header)
print(body)

def display_info(con_name):
   '''display ['Info'] data for a container'''
   data = admin_db.get_container_data(con_name)
   info = data['Info']
   print(con_name)
   for k in info.keys():
      print('%-20s: %s' % (k, info[k]))

if __name__ == '__main__':
    parser = ArgumentParser(description='unit test for admin_db module',
                            usage='%(prog)s [options] module_name')
    parser.add_argument('--info', action='store', dest='con_name', 
                        help='display the info field for a container')
    results = parser.parse_args()

    if results.con_name:
        display_info(results.con_name)
