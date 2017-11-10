import pytest
from utils.es import Elasticsearch
from fixtures.setup import docker_helper

# TODO: use ENV_VARIABLE for elasticsearch,kibana endpoint

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
    return Elasticsearch(internal_url)


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
