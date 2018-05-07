FROM ruby:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    nodejs 

RUN mkdir -p /app

COPY docker/ruby/rails/testapp /app/testapp

WORKDIR /app
