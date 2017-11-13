import pytest
from utils.es import Elasticsearch
from fixtures.setup import utils
import os
import subprocess
from urllib.parse import urlparse
import timeout_decorator

ES_CURRENT_VERSION='6.0.0-rc2'
KIBANA_CURRENT_VERSION='6.0.0-rc2'

@timeout_decorator.timeout(90)
@pytest.fixture(scope="session")
def elasticsearch():
    url = os.environ.get('ES_URL')
    if url is None:
        os.environ['ES_PORT'] = '9200'
        os.environ['ES_HOST'] = 'elasticsearch'
        os.environ['ES_NAME'] = 'elasticsearch'
        url = os.environ['ES_URL'] = "http://localhost:{}".format(os.environ['ES_PORT'])
        if os.environ.get('ES_VERSION') is None:
            os.environ['ES_VERSION'] = ES_CURRENT_VERSION
        script = "tests/fixtures/setup/elasticsearch/start.sh"
        subprocess.call([script])
        utils.wait_until_service_responding(url)
    else:
        parsed_url = urlparse(url)
        os.environ['ES_PORT'] = str(parsed_url.port)
        os.environ['ES_HOST'] = parsed_url.hostname

    return Elasticsearch(url)


@timeout_decorator.timeout(90)
@pytest.fixture(scope="session")
def kibana():
    class Kibana:
        def __init__(self, url):
            self.url = url

    url = os.environ.get('KIBANA_URL')
    if url is None:
        url = os.environ['KIBANA_URL'] = "http://localhost:5601"
        if os.environ.get('KIBANA_VERSION') is None:
            os.environ['KIBANA_VERSION'] = KIBANA_CURRENT_VERSION
        os.environ['KIBANA_PORT'] = str(urlparse(url).port)
        script = "tests/fixtures/setup/kibana/start.sh"
        subprocess.call([script])
        utils.wait_until_service_responding(url)
    return Kibana(url)
