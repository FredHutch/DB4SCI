#!/usr/bin/python
from flask import Flask

app = Flask(__name__)
app.secret_key = 'secret'

import mydb_views
