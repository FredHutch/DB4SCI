#!/usr/bin/python
import os
import time
import json
import subprocess
import container_util
import admin_db
import make_keys
from send_mail import send_mail
import pymysql
from config import Config


def auth_mariadb(dbuser, dbpass, port):
    """
    Ckeck if <dbuser> account is authorized user.
    :type dbuser: basestring
    :type dbpass: basestring
    :type port: basestring
    :returns  True/False
    """
    iport = int(port)
    try:
        conn = pymysql.connect(host=Config.container_host,
                               port=iport,
                               user=dbuser,
                               password=dbpass)
    except pymysql.err.OperationalError as e:
        print("ERROR: auth_mariadb: %s" % e)
        return False
    conn.close()
    return True


def maria_create_account(params):
    """
    :type params: dict
    """
    error_msg = 'ERROR: mariadb_util; maria_create_account; '
    error_msg += 'action: %s user: %s error: %s'
    password = Config.accounts[params['dbtype']]['admin_pass']
    iport = int(params['port'])
    try:
        conn = pymysql.connect(host=Config.container_host, port=iport,
                               user='root',
                               password=password)
    except pymysql.err.OperationalError as e:
        print("ERROR: maria_create_account, connect: %s" % e)
        return "connect error"

    cur = conn.cursor()
    # Dropping a user that does not exist is MariaDB,
    # it the use is not dropped the user create fails with existing user error
    try:
        cur.execute('DROP USER {0:s}@\'%\''.format(params['dbuser']))
    except pymysql.err.InternalError as e:
        print(error_msg % ('drop', params['dbuser'], e))
    try:
        cur.execute("CREATE USER '%s'@'%%' IDENTIFIED BY '%s'" % (
                    params['dbuser'], params['dbuserpass']))
    except pymysql.err.InternalError as e:
        print(error_msg % ('create', params['dbuser'], e))
    sql_cmd = "GRANT ALL PRIVILEGES ON *.* TO '%s'@'%%' " % params['dbuser']
    sql_cmd += "WITH GRANT OPTION"
    try:
        cur.execute(sql_cmd)
    except pymysql.err.InternalError as e:
        print(error_msg % ('grant', params['dbuser'], e))
    conn.commit()
    cur.close()
    conn.close()
    return 'ok'


def create_mariadb(params):
    """
    Create MariaDB Docker instance
    :param params: dict
    :return: Help message for end user
    """
    con_name = params['dbname']
    if container_util.container_exists(con_name):
        return "Container name %s already in use" % con_name
    dbtype = params['dbtype']
    config_dat = Config.info[params['dbtype']]
    volumes = config_dat['volumes']
    print('DEBUG: DBVOL: %s' % params['db_vol'])
    for vol in volumes:
        if vol[0] == 'DBVOL': vol[0] = params['db_vol']
        if vol[0] == 'BAKVOL': vol[0] = Config.backup_vol
    container_util.make_dirs(con_name, volumes)
    #  Add key volume, encrypt.cnf file
    result = make_keys.create_mariadb_key(con_name, params)
    port = container_util.get_max_port()
    params['port'] = port
    pub_port = config_dat['pub_ports'][0]
    params['port_bindings'] = {pub_port: (Config.container_ip,str(port))}
    env = {'MYSQL_ROOT_PASSWORD': Config.accounts[dbtype]['admin_pass'],
           'MYSQL_USER': params['dbuser'],
           'MYSQL_PASSWORD': params['dbuserpass'],}

    # create container
    container_util.make_dirs(con_name, volumes)
    cmd = config_dat['command'] + ' --ft_min_word_len=3'
    (c_id, con) = container_util.create_con(params, env, cmd)
    print("DEBUG: MariaDB created. ID=%s\n" % con['Id'])
    time.sleep(10)
    #status = maria_create_account(params)
    res = "Your MariaDB container has been created. "
    res += "Container name: %s\n\n" % con_name
    res += "Use mysql command line tools to access your new MariaDB.\n\n"
    res += "mysql --host %s --port %s --user %s --password\n\n" % (
           Config.container_host,
           params['port'],
           params['dbuser'])
    res += 'Leave the password argument blank. You will be prompted to enter '
    res += 'the password.\n\n'
    res += 'Encryption at Rest is enabled and TLS support is enabled.'
    res += 'Download TLS keys from the Documentation tab. Select "TLS '
    res += 'for MariaDB."'
    res += 'Container Status: {}'.format(con['status'])

    msg = 'MariaDB created: %s\n' % params['dbname']
    msg += 'Created by: %s <%s>\n' % (params['owner'], params['contact'])
    send_mail("DB4SCI: created MariaDB", msg)
    return res


def backup_mariadb(params):
    """ MariaDB mysqldump - full database dump. Backups are PIPED to AWS S3
    backups are run from dbaas container. Require connection to container db 
    object. Requires AWS S3 tools on dbaas.
    """
    con_name = params['dbname']
    passwd = Config.accounts['MariaDB']['admin_pass']
    (c_id, dbengine) = admin_db.get_container_type(con_name)
    data = admin_db.get_container_data('', c_id)
    port = data['Info']['Port']
    (backupdir, backup_id) = container_util.create_backupdir(con_name)
    if 'backup_type' in params:
        backup_type = params['backup_type']
    else:
        backup_type = 'NA'
    bucket = os.environ.get('AWS_BUCKET')
    s3_url = bucket + '/' + con_name + backupdir
    s3_filename = s3_url + '/dump' + backup_id + '.sql'
    s3_infopath = s3_url + '/infoschema' + backup_id + '.sql'

    # mysqldump to S3 Backups
    template = "/usr/bin/mysqldump --host %s --port %s --user=root " % (
                Config.container_ip, port)
    template += "--password=%s "
    dump_cmd = template + "--all-databases"
    cmd = dump_cmd % passwd
    aws_cmd = "aws --only-show-errors s3 cp - %s --sse" % s3_filename
    admin_db.backup_log(c_id, con_name, 'start', backup_id, backup_type, url='',
                        command=cmd, err_msg='')
    print("DEBUG: mysqdump command: %s" % cmd)
    p1 = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    p2 = subprocess.Popen(aws_cmd.split(), stdin=p1.stdout, stdout=subprocess.PIPE)
    (processed, err) = p2.communicate()
    if processed and len(processed) > 0:
        message = "MariaDB Backup error.  Container: %s" % con_name
        message += "Error message: %s" % processed 
        print(message)
        send_mail("DB4SCI: MariaDB backup", message)
    else:         
        message = '\nExecuted MariaDB dump comand:\n    '
        message += dump_cmd % 'xxxxx'
        message += "\nResult:\n" + processed 
        message += "Dump file: %s\n\n" % s3_filename
        admin_db.backup_log(c_id, con_name, 'end', backup_id, backup_type,
                            url=s3_filename, command=cmd, err_msg=processed)
    return "command", message 
 
    #info_cmd = template + "INFORMATION_SCHEMA --skip-lock-tables "
    #exec_cmd = info_cmd % passwd
    #exec_cmd += "| aws s3 cp - %s" % s3_infopath
    #print("DEBUG: mysqdump INFORMATION_SCHEMA : %s" % exec_cmd)
    # result = container_util.exec_command(con_name, exec_cmd)
    #message += '\n\nDump MariaDB Information Schema:\n    '
    #message += info_cmd % 'xxxxx'
    #message += "\nResult:\n" + result
    #message += "Dump file: %s\n\n" % s3_infopath
