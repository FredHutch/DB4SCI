#!/usr/bin/env python
import os
import sys
import argparse
import time
import container_util
import admin_db

from config import Config


def test_display():
    (db_header, db_list) = container_util.display_containers()
    print(db_header)
    print(db_list)

def delete_con(params):
    pass

if __name__ == "__main__":
    test_display()
