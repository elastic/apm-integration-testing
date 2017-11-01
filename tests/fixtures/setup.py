import pytest
from utils import docker_helper
from io import BytesIO
from elasticsearch import Elasticsearch


@pytest.fixture(scope="module")
def apm_server():
    name = "apm_server"
    ports = {'8200/tcp': 8200}
    d = '''
    FROM golang:latest
    RUN set -x && \
        apt-get update && \
        apt-get install -y --no-install-recommends \
          python-pip virtualenv build-essential && \
        apt-get clean
    WORKDIR ${GOPATH}/src/github.com/elastic/
    CMD ["/bin/bash", "-c", "rm -rf apm-server && \
        git clone http://github.com/elastic/apm-server.git &&\
        cd apm-server &&\
        make update &&\
        make &&\
        ./apm-server -E apm-server.host=0.0.0.0:8200 -E output.elasticsearch.hosts=[elasticsearch:9200]"]
    '''
    f = BytesIO(d.encode('utf-8'))
    url = "http://localhost:8200/healthcheck"

    docker_helper.build_image(name, f)
    container = docker_helper.run_container(name, ports=ports, url=url)
    return container


@pytest.fixture(scope="module")
def elasticsearch():
    version = "6.0.0-rc1"
    img_name = "docker.elastic.co/elasticsearch/elasticsearch:" + version
    container_name = "elasticsearch"
    env = {
        'ES_JAVA_OPTS': '-Xms512m -Xmx512m',
        'network.host': '',
        'transport.host': '0.0.0.0',
        'http.host': '0.0.0.0',
        'xpack.security.enabled': 'false',
    }
    ports = {'9200/tcp': 9200, '9300/tcp': 9300}
    internal_url = "http://localhost:9200"

    docker_helper.run_container(img_name,
                                ports=ports,
                                name=container_name,
                                url=internal_url,
                                env=env)
    return Elasticsearch([internal_url])


@pytest.fixture(scope="module")
def kibana():
    version = "6.0.0-rc1"
    img_name = "docker.elastic.co/kibana/kibana:" + version
    container_name = "kibana"
    ports = {'5601/tcp': 5601}
    env = {
        'network.host': '',
        'transport.host': '0.0.0.0',
        'http.host': '0.0.0.0',
    }
    internal_url = "http://localhost:5601"

    container = docker_helper.run_container(img_name,
                                            ports=ports,
                                            name=container_name,
                                            url=internal_url,
                                            env=env)
    return container
