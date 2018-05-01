# Install

## Security
   - Generate Server and Client keys for MariaDB. Provides encrypted data
in transite. The client keys are are served from the application help pages. 
   - Users are providing passwords for database.  All application traffic
is protected by TSL.
   - A script is provide to create encrypted volume for DB data.

### Neo4j 
Neo4j web is configured the TSL. Copy TSL certs to
```
$DB4SCI_ROOT/prod/neo4j/ssl
```

