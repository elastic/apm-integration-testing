import pytest
from fixtures.setup import docker_helper
from io import BytesIO

# TODO: use ENV_VARIABLE for apm_server, elasticsearch endpoint

@pytest.fixture(scope="module")
def apm_server():
    class APMServer:
        def __init__(self, url, container):
            self.url = url
            self.container = container

    name = "apm-server"
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
        ./apm-server \
            -E apm-server.host=0.0.0.0:8200 \
            -E output.elasticsearch.hosts=[elasticsearch:9200]"]
    '''
    f = BytesIO(d.encode('utf-8'))
    url = "http://localhost:8200/healthcheck"

    docker_helper.build_image(name, f)
    container = docker_helper.run_container(name, ports=ports, url=url)
    container = None
    return APMServer("http://apm-server:8200", container)
