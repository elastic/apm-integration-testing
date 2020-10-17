FROM php:7.4-apache

RUN apt-get -qq update \
 && apt-get -qq install -y --no-install-recommends \
    autoconf \
    build-essential \
    curl \
    git \
    libcurl4-openssl-dev \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /src && git clone https://github.com/elastic/apm-agent-php.git /src/apm-agent-php && \
    cd /src/apm-agent-php/src/ext && \
    phpize && ./configure --enable-elastic_apm && make clean install

COPY ext-elastic-apm.ini /usr/local/etc/php/conf.d/ext-elastic-apm.ini
COPY app /var/www/html/
