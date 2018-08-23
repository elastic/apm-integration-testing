ARG apm_server_base_image=docker.elastic.co/apm/apm-server:7.0.0-alpha1-SNAPSHOT
ARG go_version=1.10

FROM golang:${go_version} AS build

# install make update prerequisites
RUN apt-get update && apt-get install -y python-virtualenv

ARG apm_server_branch=master
ARG apm_server_repo=https://github.com/elastic/apm-server.git
RUN git clone -b $apm_server_branch ${apm_server_repo} /go/src/github.com/elastic/apm-server && \
	make -C /go/src/github.com/elastic/apm-server update apm-server && \
	sed -zri -e 's/output.elasticsearch:(\n[^\n]*){5}/output.elasticsearch:\n  hosts: ["elasticsearch:9200"]/' -e 's/  host: "localhost:8200"/  host: "0.0.0.0:8200"/' /go/src/github.com/elastic/apm-server/apm-server.yml && \
	chmod go+r /go/src/github.com/elastic/apm-server/apm-server.yml

FROM ${apm_server_base_image}

COPY --from=build /go/src/github.com/elastic/apm-server/apm-server /usr/share/apm-server/apm-server
COPY --from=build /go/src/github.com/elastic/apm-server/apm-server.yml /usr/share/apm-server/apm-server.yml
COPY --from=build /go/src/github.com/elastic/apm-server/fields.yml /usr/share/apm-server/fields.yml
