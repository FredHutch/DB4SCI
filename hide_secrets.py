#!/usr/bin/env python
import sys
import re

"""Remove secrets from Python configuration file.
   Simple text replace for secret values.
   Only one secret per line.  Secrets can be variable assignments or
   dictionary values.  Examples:

  admin_password = 'secret password'
  'non secret': 'normal value', 'admin_password': 'secret value'},

  <targets> contains a list of configuration variables to change
"""


def hide_secrets(filename):
    """Remove secrets from Python configuration files.
    """
    targets = {'admin_pass': 'secretPassword',
               'admindb_password': 'MYDB_admin PW',
               'admins': "'list', 'of', 'adminitrator', 'SIDS'",
               'backup_admin_mail': 'IgetMailAboutBackups@domain.org',
               'contact': 'mydb_admin@domain.com',
               'owner': 'Full Name',
               'container_host': 'Docker host',
               'FQDN_host': 'Docker host FQDN',
               'Container_ip': 'IP of Docker Server',
               'MAIL_TO': 'MYDB_Admin@domain.com'}
    var_re = r'(^.*=\s*[\[\'"])(.*)([\]\'"].*)'

    def replace_secrets(line, TARGET):
        dict_re = r'(.*[\'"]?' + TARGET
        dict_re += r'[\'"]?\s?:\s*[\'"])(\w[\w !@#$%^&\.\*=+]*)([\'"].*$)'
        if '=' in line:
            clean_line = re.sub(var_re, r'\1' + targets[TARGET] + r'\3', line)
            return clean_line
        if ':' in line:
            clean_line = re.sub(dict_re, r'\1' + targets[TARGET] + r'\3', line)
            return clean_line

    with open(filename) as f:
        for line in f:
            for target in targets.keys():
                if target in line:
                    line = replace_secrets(line, target)
                    break
            print(line),

if __name__ == '__main__':
    """Input: secify filename on command line
       output: written to standard out
    """
    if len(sys.argv) != 2:
        print('Must speicify a filename as argument. usage:  %s [con.fig.py]' %
              sys.argv[0])
        sys.exit(1)

    hide_secrets(sys.argv[1])
