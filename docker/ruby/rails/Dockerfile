FROM ruby:latest

RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends \
    build-essential \
    nodejs

## Whether the reference is a branch or a git commit to be used within the Gemfile
ARG RUBY_AGENT_REPO=elastic/apm-agent-ruby
ARG RUBY_AGENT_VERSION=master
ENV RUBY_AGENT_REPO=$RUBY_AGENT_REPO
ENV RUBY_AGENT_VERSION=$RUBY_AGENT_VERSION

WORKDIR /src
COPY . /src
RUN ./run.sh

RUN mkdir -p /app

COPY testapp /app/testapp

WORKDIR /app/testapp
