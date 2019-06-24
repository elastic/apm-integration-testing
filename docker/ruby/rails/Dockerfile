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

RUN git clone https://github.com/${RUBY_AGENT_REPO}.git /agent/apm-agent-ruby
RUN cd /agent/apm-agent-ruby \
  && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
  && git checkout ${RUBY_AGENT_VERSION}

RUN cd /agent/apm-agent-ruby \
    && ( git show-ref --verify refs/heads/${RUBY_AGENT_VERSION} \
          && echo 'export RUBY_AGENT_TYPE=branch' >> /tmp/branch || true )

RUN mkdir -p /app

COPY testapp /app/testapp

WORKDIR /app/testapp
