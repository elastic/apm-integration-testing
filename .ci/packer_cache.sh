#!/usr/bin/env bash

# shellcheck disable=SC1091
source /usr/local/bin/bash_standard_lib.sh

DOCKER_IMAGES="alpine:3.4
alpine:latest
busybox:latest
docker.elastic.co/beats-dev/fpm:1.11.0
docker.elastic.co/observability-ci/apm-integration-testing:daily
docker.elastic.co/observability-ci/golang-mage:1.12.4
docker.elastic.co/observability-ci/jruby:9.1-7-jdk
docker.elastic.co/observability-ci/jruby:9.2-11-jdk
docker.elastic.co/observability-ci/jruby:9.2-12-jdk
docker.elastic.co/observability-ci/jruby:9.2-8-jdk
golang:1.8
golang:1.9
golang:1.10
golang:1.11
golang:1.12
golang:1.12.4
golang:latest
haproxy:1.9
jruby:9.1
jruby:9.2
maven:3.5.3-jdk-10
mcr.microsoft.com/dotnet/core/aspnet:2.2-alpine
mcr.microsoft.com/dotnet/core/sdk:2.2
node:10
node:10.0
node:12
node:12.0
node:13
node:13.0
node:14
node:14.0
node:8-slim
node:8
node:8.6
opbeans/opbeans-frontend:latest
opbeans/opbeans-go:latest
opbeans/opbeans-java:latest
opbeans/opbeans-loadgen:latest
opbeans/opbeans-node:latest
opbeans/opbeans-python:latest
opbeans/opbeans-ruby:latest
adoptopenjdk:11-jre-hotspot
php:7-alpine
php:7.2-alpine
php:7.3-alpine
pypy:2
pypy:3
python:2.7
python:3
python:3.4
python:3.5
python:3.6
python:3.7
python:3.7-stretch
python:3.8
ruby:2.3
ruby:2.4
ruby:2.5
ruby:2.6
ruby:latest
wordpress:php7.3-fpm-alpine
"

for di in ${DOCKER_IMAGES}
do
(retry 2 docker pull "${di}") || echo "Error pulling ${di} Docker image, we continue"
done
