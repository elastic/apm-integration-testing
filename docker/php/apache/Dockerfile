FROM php:7.4-apache

RUN apt-get -qq update \
 && apt-get -qq install -y --no-install-recommends \
    autoconf \
    build-essential \
    curl \
    git \
    libcurl4-openssl-dev \
    wget \
 && rm -rf /var/lib/apt/lists/*

ARG PHP_AGENT_REPO=elastic/apm-agent-php
ARG PHP_AGENT_BRANCH=main
ARG PHP_AGENT_VERSION=
WORKDIR /src
COPY . /src
RUN ./run.sh
