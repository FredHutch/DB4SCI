## DBaaS Logs 

### Overview
The Flask application is run from a Uwsgi wrapper. The
Flask application logs and error messages are written to 
`/var/log/uwsgi/uwsgi.log`
along with the WEB logs.
From python use app.logging.error("message") or just print to stdout.
Log file location is defined in uwsgi.ini 

```bash
cat /var/log/uwsgi/uwsgi.log
```

### Debugging
Debuging has to be turned on at the flash application.  The log level
is set in webui.py.

***webui.py***
```
    app.run(host='0.0.0.0',
            threaded=True,
            debug=True
    ) 
``` 


### syslog configuration file setup
cp /mydb/repos/postgres_container_mgmt/60-mydb.conf /etc/rsyslog.d/

***logrotate***
A logrotate script is provided to purne web logs: dbaas.logrotate
