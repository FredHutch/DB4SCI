## SSL Certs for NGINX

### Description
This directroy contains your domain TSL certs.  These certs are
copied to the NGINX container at build time.
All certs need to be in PEM format.  Both crt and key files need to
be copied to this directory.  DB4SCI requires TSL support since
user pass words are sent to the application for authentication and
for configuration.

The certs are copied to the folder; /etc/ca-certificates/ on the
NGINX container.
