# Use Ubuntu 16.04 as the base container
FROM ubuntu:16.04

# Update the system and install packages
RUN apt-get -y -qq update && apt-get -y -qq install \
    python \
    python-dev \
    python-pip \
    postgresql-server-dev-all \
    libldap2-dev \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    libffi-dev \
    postgresql-client-9.5 \
    mariadb-client-10.0.33 \
    apt-transport-https \
    ca-certificates \
    docker.ce \
    uwsgi \
    uwsgi-core \
    uwsgi-plugin-python

# Create the sttrweb user and data directory
RUN mkdir /opt/dbaas && \
    mkdir /mydb && \
    mkdir /mydb/postgres_dbs && \
    mkdir /mydb/db_backups && \
    mkdir /mydb/mariadb_keys && \
    mkdir -p /var/run/postgresdb
RUN echo "140.107.170.124 loghost" >>/etc/hosts
RUN groupadd --gid 999 dbaas 
RUN useradd -u 999 -g 999 -s /bin/nologin docker

# Install Python packages

ADD requirements.txt /opt/dbaas/
RUN pip install -r /opt/dbaas/requirements.txt 


# Copy files to container
ENV env dev 
ADD *.py /opt/dbaas/
ADD ${env}/nginx/ssl /opt/dbaas/ssl
ADD ${env}/neo4j /opt/dbaas/neo4j
ADD mydb /opt/dbaas/mydb/
ADD uwsgi.ini /opt/dbaas/

# Switch to the server directory and start it up
WORKDIR /opt/dbaas

CMD ["uwsgi", "--ini", "uwsgi.ini"]
