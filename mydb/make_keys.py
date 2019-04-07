#!/usr/bin/env python

import os
import errno
import stat
import OpenSSL
import subprocess
from config import Config
import shutil
from hashlib import md5
from Crypto.Cipher import AES
from Crypto import Random

""" create keys for MariaDB encryption at rest

generate a random 128-bit encryption key with:  openssl rand 16 -hex >key.txt
# encrypt the key file
openssl enc -aes-256-cbc -P -md sha1
enter aes-256-cbc encryption password:
Verifying - enter aes-256-cbc encryption password:
salt=2C573F713EE0C3FB
key=53FA6507235FDA0B9D878B2CE6415A0B5B9F79CA73E22735FCEEA023EEF83602
iv =C9051F2BB4D4B18815EBE9426486CAB0

save like this: keys.txt
1;C9051F2BB4D4B18815EBE9426486CAB0;53FA6507235FDA0B9D878B2CE6415A0B5B9F79CA73E22735FCEEA023EEF83602

==== earlier notes =======
openssl enc -aes-256-cbc -md sha1 -k secret -in keys.txt -out keys.enc

[mysqld]
file_key_management_encryption_algorithm=aes_cbc
file_key_management_filename = /home/mdb/keys.enc
file_key_management_filekey = secret
"""


def copy_tsl(con_name, db_vol):
    """Copy TLS server keys to mairadb keys volume
    Copy MariaDB encrypt.cnf to /etc/mysql/conf.d volume
       code is run from db4sci container
    """
    files = ['server-cert.pem', 'server-key.pem', 'server-req.pem',
             'ca-cert.pem']
    source = '/opt/DB4SCI/TLS/'
    destination = db_vol + '/' + con_name + '/keys/'
    for file in files:
        print("copy %s %s" % (source + file, destination))
        shutil.copy(source + file, destination)
        os.chown(destination + file, 999, 999)
    source = '/opt/DB4SCI/dbconfig/MariaDB/encrypt.cnf'
    destination = db_vol + '/' + con_name + '/conf.d/'
    shutil.copy(source, destination)
                 

def encrypt_key_file(key_file, enc_file, password):
    ''' Encrypt contents of <key_file> and write to <enc_file> '''
    cmd_template = 'openssl enc -aes-256-cbc -md sha1 -k %s -in %s -out %s'
    cmd = cmd_template % (password, key_file, enc_file)
    print('encrypting keys: %s' % cmd)
    out = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    processed, _ = out.communicate()


def derive_key_and_iv(password):
    iv_length = AES.block_size 
    key_length = 32
    salt = Random.new().read(iv_length - len('Salted__'))
    d = d_i = ''
    while len(d) < key_length + iv_length:
        d_i = md5(d_i + password.encode('ascii','ignore') + salt).digest()
        d += d_i
    return salt, d[:key_length], d[key_length:key_length+iv_length]


def create_mariadb_key(con_name, params):
    """ create key, save to file, encrypt key file
        then delete key
    """
    password = params['dbuserpass']
    db_vol = params['db_vol']
    salt, key_hex, iv_hex = derive_key_and_iv(password)
    iv_str = ''.join('%02X' % ord(iv_hex[i]) for i in range(len(iv_hex)))
    key_str = ''.join('%02X' % ord(key_hex[i]) for i in range(len(key_hex)))
    key_path = db_vol + '/' + con_name + '/keys'
    keyfile = key_path + '/keys.txt'
    encname = key_path + '/keys.enc'
    copy_tsl(con_name, db_vol)
    # write keys.txt
    iv_key = '1;' + iv_str + ';' + key_str
    filep = open(keyfile, 'w')
    filep.write('# this is a comment\n')
    filep.write(iv_key + '\n')
    filep.flush()
    filep.close()
    # encrypt keys.txt -> keys.enc
    encrypt_key_file(keyfile, encname, 'mydbencrypt')
    
    # delete the unencrypted file
    os.remove(keyfile)

    # correct owner and permissions
    os.chown(encname, 999, 999)
    os.chmod(encname, 0o700) 
    return iv_key 

if __name__ == '__main__':
    con_name = 'test1'
    password = 'mydbencrypt'
    key_str = create_mariadb_key(con_name, password)
    print(key_str)
