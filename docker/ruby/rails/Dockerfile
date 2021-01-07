ARG RUBY_VERSION=latest
FROM ruby:${RUBY_VERSION}

RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
    build-essential \
    nodejs 

RUN mkdir -p /app

COPY testapp /app/testapp

WORKDIR /app/testapp
