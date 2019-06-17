ARG apm_server_base_image=docker.elastic.co/apm/apm-server:7.0.0-alpha1-SNAPSHOT
ARG go_version=1.11

FROM golang:${go_version} AS build

# install make update prerequisites
RUN apt-get -qq update && apt-get -qq install -y python-virtualenv

ARG apm_server_branch=master
ARG apm_server_commit=
ARG apm_server_repo=https://github.com/elastic/apm-server.git
ENV SRC=/go/src/github.com/elastic/apm-server

# Git clone and checkout given either the branch, commit or both.
RUN [ -z "${apm_server_commit}" ] \
      && (echo 'cloning from branch' && git clone -b $apm_server_branch ${apm_server_repo} ${SRC}) \
      || (echo 'cloning from commit' && git clone ${apm_server_repo} ${SRC} \
          && cd ${SRC} && git reset --hard ${apm_server_commit})

RUN cd ${SRC} && git rev-parse HEAD

RUN make -C ${SRC} && update apm-server \
	  && sed -zri -e 's/output.elasticsearch:(\n[^\n]*){5}/output.elasticsearch:\n  hosts: ["elasticsearch:9200"]/' -e 's/  host: "localhost:8200"/  host: "0.0.0.0:8200"/' ${SRC}/apm-server.yml \
	  && chmod go+r ${SRC}/apm-server.yml

FROM ${apm_server_base_image}

COPY --from=build ${SRC}/apm-server /usr/share/apm-server/apm-server
COPY --from=build ${SRC}/apm-server.yml /usr/share/apm-server/apm-server.yml
COPY --from=build ${SRC}/fields.yml /usr/share/apm-server/fields.yml
