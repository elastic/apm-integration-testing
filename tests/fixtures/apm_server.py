import pytest
from fixtures.setup import utils
import os
import subprocess
from urllib.parse import urlparse
import timeout_decorator


@timeout_decorator.timeout(90)
@pytest.fixture(scope="session")
def apm_server(elasticsearch):
    class APMServer:
        def __init__(self, url):
            self.url = url
            self.elasticsearch = elasticsearch

    url = os.environ.get('APM_SERVER_URL')
    if url is None:
        name = os.environ['APM_SERVER_NAME'] = 'apm-server'
        port = os.environ['APM_SERVER_PORT'] = "8200"
        os.environ['APM_SERVER_URL'] = "http://{}:{}".format(name, port)
        if os.environ.get('APM_SERVER_VERSION') is None:
            os.environ['APM_SERVER_VERSION'] = 'master'
        script = "tests/fixtures/setup/apm_server/start.sh"
        subprocess.call([script])
        url = "http://localhost:8200"
        healthcheck_url = "{}/healthcheck".format(url)
        utils.wait_until_service_responding(healthcheck_url)

    return APMServer(url)
