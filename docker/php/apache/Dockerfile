FROM php:7.4-apache

RUN apt-get -qq update \
 && apt-get -qq install -y --no-install-recommends \
    autoconf \
    build-essential \
    curl \
    git \
    libcurl4-openssl-dev \
<<<<<<< HEAD
    wget \
 && rm -rf /var/lib/apt/lists/*

ARG PHP_AGENT_REPO=elastic/apm-agent-php
ARG PHP_AGENT_BRANCH=main
ARG PHP_AGENT_VERSION=
WORKDIR /src
COPY . /src
RUN ./run.sh
=======
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /src && git clone https://github.com/elastic/apm-agent-php.git /src/apm-agent-php && \
    cd /src/apm-agent-php/src/ext && \
    phpize && ./configure --enable-elastic_apm && make clean install

COPY ext-elastic-apm.ini /usr/local/etc/php/conf.d/ext-elastic-apm.ini
COPY app /var/www/html/
>>>>>>> bc74219 (add basic PHP agent integration tests (#863))
