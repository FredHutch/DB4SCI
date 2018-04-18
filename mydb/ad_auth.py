#!/usr/bin/python
import ldap
import getpass
import random
import local_config

def ad_auth(username, password, server):
    """Athenticate <username>, <password> with AD
    """
    auth = 0
    ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT,0)
    l = ldap.initialize ("ldaps://" + server + ":636")
    l.protocol_version = ldap.VERSION3
    l.network_timeout = 2.5
    if not password.strip():
        auth = 0
        return auth

    if not password.replace(local_config.var.AD_domain,'').strip():
        auth = 0
        return auth

    try:
        l.simple_bind_s(username,password)
        l.unbind()
        auth = 1

    except ldap.INVALID_CREDENTIALS:
        auth = 0

    except ldap.SERVER_DOWN:
        auth = 2

    except:
        auth = 3
        
    return auth

if __name__ == "__main__":
    user = raw_input("username: ") + local_config.var.AD_domain 
    password = getpass.getpass("Password: ")

    dc_list = local_config.var.DCs
    random.shuffle(dc_list)

    for DC in dc_list:
        auth = ad_auth(user,password,DC)
        if auth == 2 or auth == 3:
            continue
        elif auth == 1 or auth == 0:
            break

    if auth == 1: 
        print "Welcome", user
    elif auth == 2:
        print "All Domain Controllers are down!!!"
    elif auth == 0:
        print "Invalid Credentials"
    else:
        print "Unknown Error"
