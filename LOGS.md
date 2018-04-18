## DBaaS Logs 

### Overview
Application logs are written to /mydb/logs/prod. uwsgi writes the Flask WEB logs. Messages written from the
Flask application are also written to uwsgi.log.  From python use app.logging.error("message")
Log file location is defined in uwsig.ini 

```bash
cat /mydb/logs/prod/uwsgi/uwsgi.log
```

***syslog***
The mydb_setup.sh installs the syslog configuration file. With syslog configured the WEB logs are
written to /var/log/messages and logged remotely to copycat via rsyslog. 

### Debugging
Debuging has to be turned on at the flash application.  The log level is set in webui.py.

***webui.py***
```
    app.run(host='0.0.0.0',
            port=5000,
            threaded=True,
            debug=True
    ) 
``` 


### syslog configuration file setup
cp /mydb/repos/postgres_container_mgmt/60-mydb.conf /etc/rsyslog.d/

***logrotate***
A logrotate script is provided to purne web logs: dbaas.logrotate
