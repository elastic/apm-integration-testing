import pytest
import os
from tests.endpoint import Endpoint
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


@pytest.fixture(scope="session")
def flask(apm_server):
    return Agent(os.environ['FLASK_SERVICE_NAME'],
                 os.environ['FLASK_URL'],
                 apm_server)


@pytest.fixture(scope="session")
def django(apm_server):
    return Agent(os.environ['DJANGO_SERVICE_NAME'],
                 os.environ['DJANGO_URL'],
                 apm_server)


@pytest.fixture(scope="session")
def express(apm_server):
    return Agent(os.environ['EXPRESS_APP_NAME'],
                 os.environ['EXPRESS_URL'],
                 apm_server)


class Agent:
    def __init__(self, app_name, url, apm_server):
        self.app_name = app_name
        self.url = url
        self.port = urlparse(url).port
        self.foo = Endpoint(self.url, "foo")
        self.bar = Endpoint(self.url, "bar")
        self.apm_server = apm_server
