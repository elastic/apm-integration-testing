try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

import pytest

from tests.endpoint import Endpoint
from tests.fixtures import default


@pytest.fixture(scope="session")
def flask(apm_server):
    return Agent(default.from_env('FLASK_SERVICE_NAME'),
                 default.from_env('FLASK_URL'),
                 apm_server)


@pytest.fixture(scope="session")
def django(apm_server):
    return Agent(default.from_env('DJANGO_SERVICE_NAME'),
                 default.from_env('DJANGO_URL'),
                 apm_server)


@pytest.fixture(scope="session")
def express(apm_server):
    return Agent(default.from_env('EXPRESS_SERVICE_NAME'),
                 default.from_env('EXPRESS_URL'),
                 apm_server)


@pytest.fixture(scope="session")
def go_nethttp(apm_server):
    return Agent(default.from_env('GO_NETHTTP_SERVICE_NAME'),
                 default.from_env('GO_NETHTTP_URL'),
                 apm_server)


@pytest.fixture(scope="session")
def rails(apm_server):
    return Agent(default.from_env('RAILS_SERVICE_NAME'),
                 default.from_env('RAILS_URL'),
                 apm_server)


@pytest.fixture(scope="session")
def java_spring(apm_server):
    return Agent(default.from_env('JAVA_SPRING_SERVICE_NAME'),
                 default.from_env('JAVA_SPRING_URL'),
                 apm_server)


class Agent:
    def __init__(self, app_name, url, apm_server):
        self.app_name = app_name
        self.url = url
        self.port = urlparse(url).port
        self.foo = Endpoint(self.url, "foo")
        self.bar = Endpoint(self.url, "bar")
        self.apm_server = apm_server
