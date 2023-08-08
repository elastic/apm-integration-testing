ARG apm_server_base_image=docker.elastic.co/apm/apm-server:8.9.0-SNAPSHOT
ARG go_version=1.20.7
ARG apm_server_binary=apm-server

###############################################################################
# Build stage: build apm-server binary and update apm-server.yml
###############################################################################

FROM golang:${go_version} AS build
ARG apm_server_binary

# install make update prerequisites
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries
RUN apt-get -qq update \
    && apt-get -qq install -y python3 python3-pip python3-venv rsync

ARG apm_server_branch_or_commit=main
ARG apm_server_repo=https://github.com/elastic/apm-server.git
ENV SRC=/go/src/github.com/elastic/apm-server

# Git clone and checkout given either the branch, commit or both.
RUN git clone ${apm_server_repo} ${SRC} \
    && cd ${SRC} && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
    && git checkout ${apm_server_branch_or_commit}

RUN cd ${SRC} && git rev-parse HEAD && echo ${apm_server_branch_or_commit}

RUN make -C ${SRC} update ${apm_server_binary} \
	  && sed -zri -e 's/output.elasticsearch:(\n[^\n]*){5}/output.elasticsearch:\n  hosts: ["\${ELASTICSEARCH_HOSTS:elasticsearch:9200}"]/' -e 's/  host: "localhost:8200"/  host: "0.0.0.0:8200"/' ${SRC}/apm-server.yml \
	  && chmod go+r ${SRC}/apm-server.yml

###############################################################################
# Image update stage: layer apm-server binary and apm-server.yml on top of the
# base image.
###############################################################################

FROM ${apm_server_base_image}
ARG apm_server_binary
ENV SRC=/go/src/github.com/elastic/apm-server
COPY --from=build ${SRC}/${apm_server_binary} /usr/share/apm-server/apm-server
COPY --from=build ${SRC}/apm-server.yml /usr/share/apm-server/apm-server.yml

CMD ./apm-server -e -d "*"

# Add healthcheck for docker/healthcheck metricset to check during testing
HEALTHCHECK CMD exit 0
