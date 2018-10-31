#!/usr/bin/python
"""mydb_view All Flask routes go here!
All flask API calls go here.
"""

__version__ = '1.7.0.1'
__date__ = 'Oct 30 2018'
__author__ = 'John Dey'

import os
import ad_auth
import json
import time
from flask import Flask, render_template, request, url_for, session, redirect
from flask import send_from_directory, jsonify
from . import app
from send_mail import send_mail
import postgres_util
import container_util
import mongodb_util
import mariadb_util
import neo4j_util
import admin_db
import local_config
import volumes


@app.route('/')
def first():
    if 'level' not in session:
        level = os.environ.get('DBAAS_ENV')
        session['level'] = "demo"
    if session['level'] == "demo":
        session['logged_in'] = True
        return render_template('demo.html', version=__version__)
    else:
        session['logged_in'] = False
        return redirect(url_for('index'))


@app.route('/index')
def index():
    if 'logged_in' in session and session['logged_in']:
        return render_template('index.html', version=__version__)
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    session['logged_in'] = False
    if request.method == 'POST':
        username = request.form['username'] + '@fhcrc.org'
        password = request.form['password']

        for DC in local_config.var.DCs:
            if DC == 'demo':
                auth = 1
                break
            auth = ad_auth.ad_auth(username, password, DC)
            if auth == 2 or auth == 3:
                continue
            elif auth == 1 or auth == 0:
                break

        if auth == 1:
            session['logged_in'] = True
            session['username'] = request.form['username']
            return redirect(url_for('index'))

        elif auth == 0:
            session['logged_in'] = False
            return "<h1>Error: Invalid Credentials</h1>"

        elif auth == 2:
            session['logged_in'] = False
            return "<h1>Error: Can't contact any domain controllers</h1>"

        else:
            session['logged_in'] = False
            return "<h1>Error: occurred validating your credentials</h1>"
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


@app.route('/list_containers/')
def list_containers():
    if session['logged_in']:
        (db_header, db_list) = container_util.display_containers()
        return render_template('dblist.html',
                               title='MyDB Database Containers',
                               dbheader=db_header, dbs=db_list)
    else:
        return redirect(url_for('login'))


# learning AJAX
@app.route('/get_container_names')
def get_container_names():
    """ display conatainer names in json """
    container_names = admin_db.list_container_names()
    container_names.sort()
    return jsonify(container_names)
    

@app.route('/create_form/', methods=['GET'])
def create_form():
    """called from layout.html
       dbtype has to be passed as an arg
       Value of dbtype has to match <info> data from local_config.py
       Example: "Postgres", "MongoDB", "MariaDB"...
    """
    if not session['logged_in']:
        return redirect(url_for('login'))
    if 'dbtype' in request.args:
        print("DEBUG: create_form: dbtype: %s" % request.args['dbtype'])
        dbtype = request.args['dbtype']
        volumes_lst = volumes.volumes(dbtype, session['username']) 
        return render_template('general_form.html', dblabel=dbtype,
                               volumes=volumes_lst,
                               image_list=local_config.info[dbtype]['images'])
    else:
        message = "ERROR: create_form: url argument dbtype is incorrect. "
        message += "check index.html template"
        print(message)
        return "<h2>" + message + "</h2>"


@app.route('/created/', methods=['POST'])
def created():
    if not session['logged_in']:
        return redirect(url_for('login'))
    params = {}
    for item in request.form:
        params[item] = request.form[item].replace(';', '').\
                                          replace('&', '').strip()
    params['username'] = session['username']
    if params['dbtype'] == 'Postgres':
        result = postgres_util.create(params)
    elif params['dbtype'] == 'MongoDB':
        result = mongodb_util.create_mongodb(params)
    elif params['dbtype'] == 'Neo4j':
        result = neo4j_util.create(params)
    elif params['dbtype'] == 'MariaDB':
        result = mariadb_util.create_mariadb(params)
    else:
        result = 'Error: file=postgres_view, def=created(), '
        result += 'message="dbtype not set in general_form.html"'
    params['result'] = result
    return render_template('created.html', **params)


@app.manage_container('/manaage_container', methods=['GET'])
def manage_container():
    """ select container name, use <action> to render the form"""
    if not session['logged_in']:
        return redirect(url_for('login'))
    action = request.args['action']
    select_title='Select Container Name to %s' % action.capitalize()
    container_names = admin_db.list_container_names()
    container_names.sort()
    return render_template('select_container.html',
                           title=select_title, 
                           header='',
                           labela='Container Name:',
                           action = action,
                           items=container_names)


@app.route('/cloudbackups/', methods=['GET'])
def cloudbackups():
    if not session['logged_in']:
        return redirect(url_for('login'))
    container_name = request.args['container_name']
    print('cloudbackups: container: %s' % container_name)
    cmd = "%s s3 ls --recursive %s/%s" % (local_config.var.aws,
                                          local_config.var.bucket,
                                          container_name)
    backups = os.popen(cmd).read().strip()
    return render_template('cloudbackups.html', con_name=container_name,
                           backups=backups)


@app.route('/restarted/', methods=['POST'])
def restarted():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['dbname'].replace(';', '').replace('&', '').strip()
    dbuser = request.form['dbuser'].replace(';', '').replace('&', '').strip()
    dbuserpass = request.form['dbuserpass'].replace(';', '').\
        replace('&', '').strip()
    username = session['username']
    result = container_util.restart_con(dbname, dbuser, dbuserpass, username)
    return render_template('restarted.html', result=result)


@app.route('/deleted/', methods=['POST'])
def deleted():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['dbname'].replace(';', '').replace('&', '').strip()
    dbuser = request.form['dbuser'].replace(';', '').replace('&', '').strip()
    dbuserpass = request.form['dbuserpass'].replace(';', '').\
        replace('&', '').strip()
    username = session['username']
    result = container_util.kill_con(dbname, dbuser, dbuserpass, username)
    return render_template('deleted.html', result=result)


@app.route('/backup/')
def backup():
    if session['logged_in']:
        container_names = admin_db.list_container_names()
        container_names.sort()
        return render_template('backup.html', items=container_names)
    else:
        return redirect(url_for('login'))


@app.route('/backedup/', methods=['POST'])
def backedup():
    if not session['logged_in']:
        return redirect(url_for('login'))
    # backtag
    params = {}
    for item in request.form:
        params[item] = request.form[item].replace(';', '').\
                                          replace('&', '').strip()
    params['username'] = session['username']
    params['backup_type'] = 'User'
    if 'backuptag' in params:
        backuptag = params['backuptag']
    else:
        backuptag = None

    (c_id, dbengine) = admin_db.get_container_type(params['dbname'])
    if c_id is None:
        result='Database container not found. %s' % params['dbname']
        return  render_template('backedup.html', result=result)
    if dbengine == 'MongoDB':
        (cmd, mesg) = mongodb_util.backup_mongodb(params['dbname'], 'User')
        result = "mongodump executed:\n" + cmd + "\nResults\n" + mesg 
    elif dbengine == 'MariaDB':
        (cmd, mesg) = mariadb_util.backup_mariadb(params)
        result = "MariaDB Backup\n" + mesg
    elif dbengine == 'Neo4j':
        (cmd, mesg) = neo4j_util.backup(params)
        result = "Neo4j graph.db copied:\n" + cmd + "\nResult: %s" % mesg
    else:
        (cmd, mesg) = postgres_util.backup(params, params['backuptag'])
        result = "Postgres dump comand:\n" + cmd + "\nResult: %s" % mesg
    return render_template('backedup.html', result=result)


def admin_help():
        body = 'MyDB administrators must be added to local_config.admins.\n'
        body += 'append admin commands to URL\n'
        body += '/admin/help/   Your reading it.\n'
        body += '/admin/state/  Display all records in State table\n'
        body += '/admin/list Display running containers\n'
        body += '/admin/du/  File System du for container data volume\n'
        body += '/admin/log/  Display all records from ActionLog table\n'
        body += '/admin/info?[name=xx | cid=n]   Display Info data from'
        body += ' containers table.\n'
        body += '/admin/containers   Display summary from containers\n'
        body += '/admin/data?cid=n  Display Docker inspect from AdminDB\n'
        body += '/admin/update?cid=n&key=value&...  Update Info with new '
        body += 'key: values\n'
        body += '/admin/delete?name=container_name\n'
        body += '/admin/setMaintenance[?done]  Change state to/from '
        body += '"maintenance"\n\n'
        body += 'URL encoding tips:  Space: %20, @: %40\n'
        return body

@app.route('/admin/<cmd>')
def admin(cmd):
    if not session['logged_in']:
        return redirect(url_for('login'))
    elif session['username'] not in local_config.var.admins:
        title = 'User ' + session['username']
        title += ' not in list of admins. Update local_config.admins'
        return render_template('dblist.html', Error=True, title=title,
                               dbheader='', dbs='')
    username = session['username']
    if cmd == 'help':
        body = admin_help()
        title = 'MyDB Administrative Features\n'
        return render_template('dblist.html', title=title,
                               dbheader='', dbs=body)
    elif cmd == 'state':
        (header, body) = admin_db.display_container_state()
        return render_template('dblist.html', title='Admin DB State Table',
                               dbheader=header, dbs=body)
    elif cmd == 'list':
        (header, body) = admin_db.display_active_containers()
        return render_template('dblist.html', title='Active Containers',
                               dbheader=header, dbs=body)
    elif cmd == 'containers':
        (header, body) = admin_db.display_containers()
        return render_template('dblist.html', title='Containers Summary',
                               dbheader=header, dbs=body)
    elif cmd == 'du':
        body = admin_db.du_all()
        return render_template('dblist.html', title='File System du',
                               dbheader='', dbs=body)
    elif cmd == 'log':
        (header, body) = admin_db.display_container_log()
        return render_template('dblist.html', title='Admin DB Log',
                               dbheader=header, dbs=body)
    elif cmd == 'data':
        if 'cid' in request.args:
            data = admin_db.get_container_data('', c_id=request.args['cid'])
            body = json.dumps(data, indent=4)
            title = 'Container Inspect from admindb'
            return render_template('dblist.html', title=title,
                                   dbheader='', dbs=body)
    elif cmd == 'info':
        cid = None
        if 'name' in request.args:
            body = admin_db.display_container_info(request.args['name'])
        elif 'cid' in request.args:
            cid = request.args['cid']
            body = admin_db.display_container_info('', c_id=cid)
        else:
            return 'DEBUG: admin-info: No URL arguments'
        title = 'Container Info '   # for %s' % body['Name']
        return render_template('dblist.html', title=title,
                               dbheader='', dbs=body)
    elif cmd == 'update':
        info = {}
        for item in request.args.keys():
            if 'cid' != item:
                info[item] = request.args[item]
        if 'cid' in request.args and len(info.keys()) > 0:
            admin_db.update_container_info(request.args['cid'], info)
            return 'Updated Info\n' + json.dumps(info, indent=4)
        else:
            return 'DEBUG: admin-update: No URL arguments'
    elif cmd == 'delete':
        if 'name' in request.args:
            name = request.args['name']
        username = session['username']
        result = container_util.admin_kill(name, username)
        return render_template('deleted.html', result=result)
    elif cmd == 'setMaintenance':
        new_state = 'maintenance'
        message = 'All containers set to "maintenance"'
        state_info = admin_db.get_container_state()
        if 'done' in request.args:
            new_state = 'running'
            message = 'All containers set to "running"'
        for state in state_info:
            admin_db.update_container_state(state.c_id, new_state,
                                            who=session['username'])
        return message
    else:
        return 'incorect admin URL'


@app.route('/certs/<filename>', methods=['GET'])
def certs(filename):
    return send_from_directory(directory=local_config.var.dbaas_path + '/TLS',
                               as_attachment=True, 
                               filename=filename + '.pem')

@app.route('/doc_page/')
def doc_page():
    doc_name = request.args['doc']
    doc_name += '.html'
    return render_template(doc_name)
