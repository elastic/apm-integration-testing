FROM ruby:latest

RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
    build-essential \
    nodejs 

RUN mkdir -p /app

COPY testapp /app/testapp

WORKDIR /app/testapp
