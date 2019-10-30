# Install

## Security
 - Generate Server and Client keys for MariaDB. Provides encrypted data
in transite. The client keys are are served from the application help pages. 
 - edit TLS/ca.cnf, server.cnf and client.cnf files. Change the
      distinguished name to your organization. 
   ```
   su -s /bin/bash docker
   cd /opt/DB4SCI/TLS
   # edit ca.cnf, server.cnf and client.cnf
   rm *.pem
   bash TLS-create.sh
   ```
   - A script is provided to create encrypted volume for DB data.

### Neo4j 
Neo4j web is configured for TSL. Copy TSL certs to
```
$DB4SCI_ROOT/prod/neo4j/ssl
```

