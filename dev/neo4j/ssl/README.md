## Neo4j Configuration

$MYDB_BASE/prod/neo4j/ssl

MyDB configures Neo4j to use TLS on the http port. Put your sites certificates
in this directory.  The certs will be copied into the Neo4j container during 
build.  Neo4j requires the file names to be;
neo4j.cert and neo4j.key
