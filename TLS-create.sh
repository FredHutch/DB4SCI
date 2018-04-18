#!/bin/bash

# Generate client/server TLS keys for MariaDB
# CA should only be generated once during install. 
#
# CA expires in 5 years.  remove TLS/ca-cert.pem and re-run script 
#

if [[ ! -d TLS ]]; then
    mkdir TLS
fi
cd TLS 

if [[ -e ca-cert.pem ]]; then
    echo CA exists. It should not be changed.
    exit 0
fi

echo '> create CA Key'
openssl genrsa 4096 > ca-key.pem

echo '> create CA'
openssl req -new -x509 -nodes -days 1825 -config ca.cnf -key ca-key.pem -out ca-cert.pem

echo '> Create the server certificate'
openssl req -newkey rsa:4096 -config server.cnf -nodes -keyout server-key.pem -out server-req.pem

echo '> Process the server RSA key'
openssl rsa -in server-key.pem -out server-key.pem

echo '> Sign the server certificate'
openssl x509 -req -in server-req.pem -days 1825 -CA ca-cert.pem -CAkey ca-key.pem -CAkey ca-key.pem -set_serial 01 -out server-cert.pem

echo '> life of cert'
openssl x509 -enddate -noout -in server-cert.pem

echo '> Create client certificate'
openssl req -newkey rsa:4096 -config client.cnf -nodes -keyout client-key.pem -out client-req.pem

echo '> Process the client RSA key'
openssl rsa -in client-key.pem -out client-key.pem

echo '> Sign the client certificate'
openssl x509 -req -in client-req.pem -days 1825 -CA ca-cert.pem -CAkey ca-key.pem -set_serial 01 -out client-cert.pem

# Combine server and client CA certificate into a single file:
cat server-cert.pem client-cert.pem > ca.pem

# chown to mysql (999)
chown 999:999 *

# Copy client cert to static area for download
echo Copy certs to static
cp ca-cert.pem    ../mydb/static
cp client-cert.pem ../mydb/static
cp client-key.pem  ../mydb/static

echo Finished creating Certs
