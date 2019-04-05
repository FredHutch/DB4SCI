#!/usr/bin/python
"""mydb_view All Flask routes go here!
All flask API calls go here.
"""

__version__ = '1.7.1.0'
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
from config import Config
import volumes


@app.before_first_request
def activate_job():
    if 'level' in session:
        print("DEBUG: before_first_request, level is set: {}".format(session['level']))
    session['logged_in'] = False
    level = os.environ.get('DB4SCI_MODE')
    print("DEBUG: before_first_request: {}".format(level))
    if level:
        session['level'] = level
    else:
        print("DEBUG: level not set. DB4SCI_MODE must be set") 
    if session['level'] == "demo":
        print("DEBUG: DB4Sci running in demo mode.") 
        session['logged_in'] = True
        session['username'] = 'demo'

@app.route('/index')
@app.route('/')
def root():
    if session['level'] == "demo":
        return redirect(url_for('demo'))
    if session['logged_in']:
        return render_template('index.html',
                               level=session['level'],
                               version=__version__)
    else:
        return redirect(url_for('login'))


@app.route('/demo')
def demo():
    return render_template('demo.html',
                           level=session['level'],
                           version=__version__)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session['level'] == 'demo':
        return redirect(url_for('demo'))
    if session['logged_in']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'] + '@fhcrc.org'
        password = request.form['password']

        for DC in Config.DCs:
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
            return redirect(url_for('root'))

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
                               title='DB4SCI Database Containers',
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
       Value of dbtype has to match <info> data from Config.py
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
                               image_list=Config.info[dbtype]['images'])
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


@app.route('/manage_container', methods=['GET'])
def manage_container():
    """ select container name, use <action> to render the form"""
    if not session['logged_in']:
        return redirect(url_for('login'))
    print('lets manage\n')
    dbaction = request.args['dbaction']
    select_title='Select Container Name to %s' % dbaction.capitalize()
    container_names = admin_db.list_container_names()
    container_names.sort()
    return render_template('manage_container.html',
                           title=select_title, 
                           header='',
                           labela='Container Name:',
                           dbaction = dbaction,
                           items=container_names)


@app.route('/S3_list/', methods=['POST'])
def S3_list():
    if not session['logged_in']:
        return redirect(url_for('login'))
    container_name = request.form['container_name']
    print('S3_list: level: %s container: %s' % (
          session['level'],container_name))
    cmd = "%s s3 ls --recursive %s/%s" % (Config.aws,
                                          Config.bucket,
                                          container_name)
    if session['level'] == "demo":
        result = "Unable to run AWS commands in demo mode.\n"
        result = cmd
    else:
        result = os.popen(cmd).read().strip()
    return render_template('results.html', title='S3 Backup',
                           container_name=container_name,
                           result=result)


@app.route('/restart/', methods=['POST'])
def restart():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['container_name']
    dbuser = request.form['dbuser'].replace(';', '').replace('&', '').strip()
    dbuserpass = request.form['dbuserpass'].replace(';', '').\
        replace('&', '').strip()
    username = session['username']
    result = container_util.restart_con(dbname, dbuser, dbuserpass, username)
    return render_template('results.html', title='Restarted Container',
                           container_name=dbname,
                           result=result)

@app.route('/delete/', methods=['POST'])
def delete():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['container_name']
    dbuser = request.form['dbuser'].replace(';', '').replace('&', '').strip()
    dbuserpass = request.form['dbuserpass'].replace(';', '').\
        replace('&', '').strip()
    username = session['username']
    result = container_util.kill_con(dbname, dbuser, dbuserpass, username)
    return render_template('results.html', title='Delete Container',
                           container_name=dbname,
                           result=result)

@app.route('/backup/', methods=['POST'])
def backup():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['container_name']
    if session['level'] == "demo":
        result = "Backup not supported in demo mode."
        return render_template('results.html',
                               title='Database Backup',
                               container_name=dbname,
                               result=result)

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
    return render_template('results.html',
                           title='Database Backup',
                           result=result)

@app.route('/restore/', methods=['POST'])
def restore():
    if not session['logged_in']:
        return redirect(url_for('login'))
    dbname = request.form['container_name']
    if session['level'] == "demo":
        result = "Restore not supported in demo mode."
    else:
        pass
        # TODO
    return render_template('results.html',
                           title='Database Restore',
                           container_name=dbname,
                           result=result)

def admin_help():
        body = 'DB4SCI administrators must be added to Config.admins.\n'
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
    elif session['username'] not in Config.admins:
        title = 'User ' + session['username']
        title += ' not in list of admins. Update Config.admins'
        return render_template('dblist.html', Error=True, title=title,
                               dbheader='', dbs='')
    username = session['username']
    if cmd == 'help':
        body = admin_help()
        title = 'DB4SCI Administrative Features\n'
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
    return send_from_directory(directory=Config.dbaas_path + '/TLS',
                               as_attachment=True, 
                               filename=filename + '.pem')

@app.route('/doc_page/')
def doc_page():
    doc_name = request.args['doc']
    doc_name += '.html'
    return render_template(doc_name,
                           level=session['level'],
                           version=__version__
                           )
