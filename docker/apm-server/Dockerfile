ARG apm_server_base_image=docker.elastic.co/apm/apm-server:8.0.0-SNAPSHOT
ARG go_version=1.12

FROM golang:${go_version} AS build

# install make update prerequisites
RUN apt-get -qq update && apt-get -qq install -y python-virtualenv

ARG apm_server_branch_or_commit=master
ARG apm_server_repo=https://github.com/elastic/apm-server.git
ENV SRC=/go/src/github.com/elastic/apm-server

# Git clone and checkout given either the branch, commit or both.
RUN git clone ${apm_server_repo} ${SRC} \
    && cd ${SRC} && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' \
    && git checkout ${apm_server_branch_or_commit}

RUN cd ${SRC} && git rev-parse HEAD && echo ${apm_server_branch_or_commit}

RUN make -C ${SRC} update apm-server \
	  && sed -zri -e 's/output.elasticsearch:(\n[^\n]*){5}/output.elasticsearch:\n  hosts: ["elasticsearch:9200"]/' -e 's/  host: "localhost:8200"/  host: "0.0.0.0:8200"/' ${SRC}/apm-server.yml \
	  && chmod go+r ${SRC}/apm-server.yml

FROM ${apm_server_base_image}
ENV SRC=/go/src/github.com/elastic/apm-server
COPY --from=build ${SRC}/apm-server /usr/share/apm-server/apm-server
COPY --from=build ${SRC}/apm-server.yml /usr/share/apm-server/apm-server.yml
COPY --from=build ${SRC}/fields.yml /usr/share/apm-server/fields.yml
