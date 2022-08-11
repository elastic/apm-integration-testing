import pytest
from .. import docker_bump

@pytest.fixture
def docker_lines_fixture():
    return [
"ARG apm_server_base_image=docker.elastic.co/apm/apm-server:8.0.0-SNAPSHOT",
"ARG apm_server_base_image=docker.elastic.co/apm/apm-server:8.0.0-SNAPSHOT",
"ARG go_version=1.17.11",
"ARG apm_server_binary=apm-server",
"\n",
"###############################################################################",
"# Build stage: build apm-server binary and update apm-server.yml",
"###############################################################################",
"\n",
"FROM golang:${go_version} AS build",
"ARG apm_server_binary",
"\n",
"# install make update prerequisites",
"RUN apt-get -qq update && apt-get -qq install -y python3 python3-pip python3-venv rsync",
"\n",
"RUN pip3 install --upgrade pip",
"\n",
"ARG apm_server_branch_or_commit=main",
"ARG apm_server_repo=https://github.com/elastic/apm-server.git",
"ENV SRC=/go/src/github.com/elastic/apm-server",
"\n",
"# Git clone and checkout given either the branch, commit or both.",
"RUN git clone ${apm_server_repo} ${SRC} && cd ${SRC} && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' && git checkout ${apm_server_branch_or_commit}",
"\n"
"RUN cd ${SRC} && git rev-parse HEAD && echo ${apm_server_branch_or_commit}",
"\n",
"###############################################################################",
"# Image update stage: layer apm-server binary and apm-server.yml on top of the",
"# base image.",
"###############################################################################",
"\n",
"FROM ${apm_server_base_image}",
"ARG apm_server_binary",
"ENV SRC=/go/src/github.com/elastic/apm-server",
"COPY --from=build ${SRC}/${apm_server_binary} /usr/share/apm-server/apm-server",
"COPY --from=build ${SRC}/apm-server.yml /usr/share/apm-server/apm-server.yml",
"\n"
"CMD ./apm-server -e -d \"*\"",
"\n"
"# Add healthcheck for docker/healthcheck metricset to check during testing",
"HEALTHCHECK CMD exit 0",
"ARG go_version=1.17.11",
"ARG apm_server_binary=apm-server",
"\n"
"###############################################################################",
"# Build stage: build apm-server binary and update apm-server.yml",
"###############################################################################",
"\n",
"FROM golang:${go_version} AS build",
"ARG apm_server_binary",
"\n",
"# install make update prerequisites",
"RUN apt-get -qq update && apt-get -qq install -y python3 python3-pip python3-venv rsync",
"\n",
"RUN pip3 install --upgrade pip",
"\n",
"ARG apm_server_branch_or_commit=main",
"ARG apm_server_repo=https://github.com/elastic/apm-server.git",
"ENV SRC=/go/src/github.com/elastic/apm-server",
"\n",
"# Git clone and checkout given either the branch, commit or both.",
"RUN git clone ${apm_server_repo} ${SRC} && cd ${SRC} && git fetch -q origin '+refs/pull/*:refs/remotes/origin/pr/*' && git checkout ${apm_server_branch_or_commit}",
"\n",
"RUN cd ${SRC} && git rev-parse HEAD && echo ${apm_server_branch_or_commit}",
"\n",
"###############################################################################",
"# Image update stage: layer apm-server binary and apm-server.yml on top of the",
"# base image.",
"###############################################################################",
"\n",
"FROM ${apm_server_base_image}",
"ARG apm_server_binary",
"ENV SRC=/go/src/github.com/elastic/apm-server",
"COPY --from=build ${SRC}/${apm_server_binary} /usr/share/apm-server/apm-server",
"COPY --from=build ${SRC}/apm-server.yml /usr/share/apm-server/apm-server.yml",
"\n",
"CMD ./apm-server -e -d \"*\"",
"\n",
"# Add healthcheck for docker/healthcheck metricset to check during testing",
"HEALTHCHECK CMD exit 0",
]

def test_version():
    assert docker_bump.__version__ == "0.1.0"

def test_docker_extract_image(docker_lines_fixture):
    assert docker_bump.docker_extract_image(docker_lines=docker_lines_fixture) == ['golang:${go_version}', '${apm_server_base_image}', 'golang:${go_version}', '${apm_server_base_image}']

def test_maven_tag_match():
    assert docker_bump._filter_maven_tags(
        ["3.6.3-adoptopenjdk-11", "buster", "3.6.3-adoptopenjdk-12"]
    ) == ["3.6.3-adoptopenjdk-11"]
