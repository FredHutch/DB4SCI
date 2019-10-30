# Use Ubuntu 16.04 as the base container
FROM ubuntu:16.04

# Update the system and install packages
RUN apt-get -y -qq update && apt-get -y -qq install \
    docker.io \
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
    libmysqlclient-dev \
    mariadb-client-10.0 \
    apt-transport-https \
    ca-certificates \
    uwsgi \
    uwsgi-core \
    uwsgi-plugin-python \
    curl \
    software-properties-common

# install docker-ce
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" && \
    apt-get -y -qq update && \
    apt-get -y -qq install docker-ce

# Create the sttrweb user and data directory
RUN mkdir /opt/DB4SCI && \
    mkdir /mydb && \
    mkdir /mydb/db_data && \
    mkdir /mydb/db_backups && \
    mkdir -p /var/run/postgresdb

RUN groupadd -f --gid 999 db4sci
RUN useradd -u 999 -g 999 -s /bin/nologin docker

# Install Python packages

ADD requirements.txt /opt/DB4SCI/
RUN pip install pip==9.0.1 && pip install -r /opt/DB4SCI/requirements.txt

# Copy files to container
ENV env dev 
ADD *.py /opt/DB4SCI/
#ADD ${env}/neo4j /opt/DB4SCI/neo4j
ADD TLS /opt/DB4SCI/TLS
ADD dbconfig /opt/DB4SCI/dbconfig
ADD mydb /opt/DB4SCI/mydb/
ADD uwsgi.ini /opt/DB4SCI/

# Switch to the server directory and start it up
WORKDIR /opt/DB4SCI

CMD ["uwsgi", "--ini", "uwsgi.ini"]
