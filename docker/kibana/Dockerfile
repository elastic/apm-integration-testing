ARG kibana_base_image=docker.elastic.co/kibana/kibana:8.0.0-SNAPSHOT
ARG node_version=

FROM node:${node_version} AS build

ARG kibana_branch_or_commit=master
ARG kibana_repo=https://github.com/elastic/kibana.git
ENV SRC=/src/kibana
WORKDIR ${SRC}

# Install dependencies:
#   https://github.com/elastic/kibana/blob/master/CONTRIBUTING.md#building-os-packages
RUN apt-get update -qq \
    && apt-get install -qq -y ruby-dev rpm \
    && gem install fpm -v 1.5.0

# Git clone and checkout given either the branch, commit or both.
RUN git clone ${kibana_repo} ${SRC} \
    && cd ${SRC} \
    && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' || true \
    && git checkout ${kibana_branch_or_commit}

RUN git rev-parse HEAD && echo ${kibana_branch_or_commit}

USER kibana
RUN sed -i bck 's#--all-platforms##g' package.json

RUN yarn kbn bootstrap \
    && yarn build --docker --no-oss --skip-os-packages --skip-archives

FROM ${kibana_base_image}
ENV SRC=/src/github.com/elastic/kibana
COPY --from=build --chown=1000:0 ${SRC}/bin/kibana-docker /usr/local/bin/