#!/usr/bin/env bash

source /usr/local/bin/bash_standard_lib.sh

DOCKER_IMAGES="golang:latest
golang:1.11
golang:1.10
haproxy:1.9
maven:3.5.3-jdk-10
openjdk:10-jre-slim
mcr.microsoft.com/dotnet/core/sdk:2.2
mcr.microsoft.com/dotnet/core/aspnet:2.2
node:8
node:8-slim
opbeans/opbeans-java:latest
opbeans/opbeans-node:latest
opbeans/opbeans-python:latest
opbeans/opbeans-ruby:latest
python:2.7
python:3
python:3.4
python:3.5
python:3.6
python:3.7
pypy:2
pypy:3
ruby:latest
ruby:2.6
ruby:2.5
ruby:2.4
ruby:2.3
jruby:9.2
jruby:9.1
node:12
node:12.0
node:11
node:11.0
node:10
node:10.0
node:8
node:8.1
node:6
node:6.0
docker.elastic.co/observability-ci/apm-integration-testing:daily
"

for di in ${DOCKER_IMAGES}
do
(retry 2 docker pull ${di}) || echo "Error pulling ${di} Docker image, we continue"
done
