from re import I
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
        "\n" 'CMD ./apm-server -e -d "*"',
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
        'CMD ./apm-server -e -d "*"',
        "\n",
        "# Add healthcheck for docker/healthcheck metricset to check during testing",
        "HEALTHCHECK CMD exit 0",
    ]


@pytest.fixture
def java_env():
    expected_java_env = {
        "JAVA_AGENT_BRANCH": "",
        "JAVA_AGENT_REPO": "elastic/apm-agent-java",
        "OPBEANS_JAVA_IMAGE": "opbeans/opbeans-java",
        "OPBEANS_JAVA_VERSION": "latest",
        "ELASTIC_APM_SERVICE_NAME": "opbeans-java",
        "ELASTIC_APM_SERVICE_VERSION": "9c2e41c8-fb2f-4b75-a89d-5089fb55fc64",
        "ELASTIC_APM_APPLICATION_PACKAGES": "co.elastic.apm.opbeans",
        "ELASTIC_APM_SERVER_URL": "http://apm-server:8200",
        "ELASTIC_APM_VERIFY_SERVER_CERT": "true",
        "ELASTIC_APM_FLUSH_INTERVAL": "5",
        "ELASTIC_APM_TRANSACTION_MAX_SPANS": "50",
        "ELASTIC_APM_ENABLE_LOG_CORRELATION": "true",
        "DATABASE_URL": "jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure",
        "DATABASE_DIALECT": "POSTGRESQL",
        "DATABASE_DRIVER": "org.postgresql.Driver",
        "REDIS_URL": "redis://redis:6379",
        "ELASTICSEARCH_URL": "http://elasticsearch:9200",
        "OPBEANS_SERVER_PORT": "3000",
        "OPBEANS_DT_PROBABILITY": "0.50",
        "ELASTIC_APM_ENVIRONMENT": "production",
        "ELASTIC_APM_TRANSACTION_SAMPLE_RATE": "0.10",
        "ELASTIC_APM_PROFILING_INFERRED_SPANS_ENABLED": "true",
    }
    return expected_java_env


def test_version():
    assert docker_bump.__version__ == "0.1.0"


def test_docker_extract_image(docker_lines_fixture):
    assert docker_bump.docker_extract_image(docker_lines=docker_lines_fixture) == [
        "golang:${go_version}",
        "${apm_server_base_image}",
        "golang:${go_version}",
        "${apm_server_base_image}",
    ]


def test_maven_tag_match():
    assert docker_bump._filter_maven_tags(
        ["3.6.3-adoptopenjdk-11", "buster", "3.6.3-adoptopenjdk-12"]
    ) == ["3.6.3-adoptopenjdk-11"]


def test_adoptopenjdk_tags():
    assert docker_bump._filter_adoptopenjdk_tags(
        ["3.6.3-adoptopenjdk-11", "buster", "3.6.3-adoptopenjdk-12"]
    ) == ["3.6.3-adoptopenjdk-11"]


def test_node_tags():
    assert docker_bump._filter_node_tags(
        [
            "18-bullseye-slim",
            "16-bullseye-slim",
            "14-bullseye-slim",
            "lts-alpine3.16",
            "lts-alpine3.15",
            "lts-alpine",
            "gallium-alpine3.16",
            "gallium-alpine3.15",
            "gallium-alpine",
            "fermium-alpine3.16",
            "fermium-alpine3.15",
            "fermium-alpine",
            "16.16.0-alpine3.16",
            "16.16.0-alpine3.15",
            "16.16.0-alpine",
            "16.16-alpine3.16",
            "16.16-alpine3.15",
        ],
        "16-bullseye-slim",
    ) == ["18-bullseye-slim", "16-bullseye-slim", "14-bullseye-slim"]


def test_agent_tags():
    assert docker_bump._filter_agent_tags(
        [
            "8.3.3-SNAPSHOT",
            "8.3.3-arm64",
            "8.3.3-amd64",
            "8.3.3",
            "8.3.2-arm64",
            "8.3.2-amd64",
            "8.3.2",
            "8.3.1-arm64",
            "8.3.1-amd64",
            "8.3.1",
            "8.3.0-arm64",
            "8.3.0-amd64",
            "8.3.0",
            "8.2.3-arm64",
            "8.2.3-amd64",
        ],
        "8.0.0-SNAPSHOT",
    ) == ["8.3.3-SNAPSHOT"]


def test_golang_tags():
    assert docker_bump._filter_golang_tags(
        [
            "alpine3.16",
            "alpine3.15",
            "alpine",
            "1.19.0-alpine3.16",
            "1.19.0-alpine3.15",
            "1.19.0-alpine",
            "1.19-alpine3.16",
            "1.19-alpine3.15",
            "1.19-alpine",
            "1.18.5-alpine3.16",
            "latest",
            "1.18.5-alpine3.15",
            "1.18.5-alpine",
            "1.18-alpine3.16",
        ],
        "latest",
    ) == ["alpine", "latest"]


def test_php_tags():
    assert docker_bump._filter_php_tags(
        [
            "zts-alpine3.16",
            "zts-alpine3.15",
            "zts-alpine",
            "fpm-alpine3.16",
            "fpm-alpine3.15",
            "fpm-alpine",
            "cli-alpine3.16",
            "cli-alpine3.15",
            "cli-alpine",
            "alpine3.16",
            "alpine3.15",
            "alpine",
            "8.2.0beta2-zts-alpine3.16",
            "8.2.0beta2-zts-alpine3.15",
            "8.1.9-apache",
        ]
    ) == ["8.1.9-apache"]


def test_statsd_tags():
    assert docker_bump._filter_statsd_tags(
        ["latest", "v0.9.0", "v0.8.6", "v0.8.5", "v0.8.4", "v0.8.3", "v0.8.2"]
    ) == ["v0.9.0", "v0.8.6", "v0.8.5", "v0.8.4", "v0.8.3", "v0.8.2"]


def test_stack_tags():
    assert docker_bump._filter_stack_tags(
        [
            "8.3.3-SNAPSHOT",
            "8.3.3-arm64",
            "8.3.3-amd64",
            "8.3.3",
            "8.3.2-arm64",
            "8.3.2-amd64",
            "8.3.2",
            "8.3.1-arm64",
            "8.3.1-amd64",
            "8.3.1",
            "8.3.0-arm64",
            "8.3.0-amd64",
            "8.3.0",
            "8.2.3-arm64",
            "8.2.3-amd64",
        ]
    ) == ["8.3.3-SNAPSHOT"]


def test_version_number():
    assert docker_bump._filter_version_number(
        [
            "alpine3.16",
            "alpine3.15",
            "alpine",
            "1.19.0-alpine3.16",
            "1.19.0-alpine3.15",
            "1.19.0-alpine",
            "1.19-alpine3.16",
            "1.19-alpine3.15",
            "1.19-alpine",
            "1.18.5-alpine3.16",
            "latest",
            "1.18.5-alpine3.15",
            "1.18.5-alpine",
            "1.18-alpine3.16",
            "1.19.0",
            "1.19",
            "1.18.5",
            "1.18",
            "1.17.13",
            "1.17",
            "1.18.4",
            "1.17.12",
            "1.18.3",
            "1.17.11",
        ]
    ) == [
        "1.19.0",
        "1.19",
        "1.18.5",
        "1.18",
        "1.17.13",
        "1.17",
        "1.18.4",
        "1.17.12",
        "1.18.3",
        "1.17.11",
    ]


def test_collect_stack_env():
    expected = {
        "apm_server_base_image": "docker.elastic.co/apm/apm-server:8.0-SNAPSHOT",
        "apm_server_branch_or_commit": "HEAD",
        "apm_server_repo": "main",
        "apm_server_binary": "apm-server",
    }
    assert docker_bump.collect_stack_env("intake-receiver") == expected


def test_collect_opbean_env(java_env):
    assert docker_bump.collect_opbean_env("java") == java_env


def test_merge_env_to_directive_no_sub(java_env):
    assert (
        docker_bump.merge_env_to_directive(java_env, "opbeans/opbeans-java:latest")
        == "opbeans/opbeans-java:latest"
    )


def test_merge_env_to_directive_sub_from_env():
    # Stub out an env
    test_env = {"IMAGE_NAME": "fake_image_name", "IMAGE_TAG": "fake_image_tag"}
    img_str = "${IMAGE_NAME}:${IMAGE_TAG}"
    assert (
        docker_bump.merge_env_to_directive(test_env, img_str)
        == "fake_image_name:fake_image_tag"
    )


def test_merge_env_to_directive_with_args():
    test_env = {}
    img_str = "${IMAGE_NAME}:${IMAGE_TAG}"
    docker_lines = ["ARG IMAGE_NAME=fake_image_name", "ARG IMAGE_TAG=fake_image_tag"]
    assert (
        docker_bump.merge_env_to_directive(test_env, img_str, docker_lines=docker_lines)
        == "fake_image_name:fake_image_tag"
    )
