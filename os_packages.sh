#!/bin/bash
#
# install OS packages
#

# Update the system and install packages
apt-get -y -qq update && apt-get -y -qq install \
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
    postgresql-client-common \
    libmysqlclient-dev \
    mariadb-client-10.0 \
    apt-transport-https \
    ca-certificates \
    uwsgi \
    uwsgi-core \
    uwsgi-plugin-python \
    curl \
    software-properties-common

# add web user to Docker group
usermod -aG docker 999

# Install Python packages
# pip install pip==9.0.1 && pip install -r /opt/dbaas/requirements.txt 
