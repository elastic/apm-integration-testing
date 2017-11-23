import pytest
import os
from urllib.parse import urlparse


@pytest.fixture(scope="session")
def flask(apm_server):
    return Agent(os.environ['FLASK_APP_NAME'],
                 os.environ['FLASK_URL'],
                 apm_server)


@pytest.fixture(scope="session")
def flask_gunicorn(apm_server):
    return Agent(os.environ['GUNICORN_APP_NAME'],
                 os.environ['GUNICORN_URL'],
                 apm_server)


@pytest.fixture(scope="session")
def django(apm_server):
    return Agent(os.environ['DJANGO_APP_NAME'],
                 os.environ['DJANGO_URL'],
                 apm_server)


@pytest.fixture(scope="session")
def express(apm_server):
    return Agent(os.environ['EXPRESS_APP_NAME'],
                 os.environ['EXPRESS_URL'],
                 apm_server)


class Endpoint:
    def __init__(self, base_url, endpoint, text=None, status_code=200):
        self.url = "{}/{}?{}".format(base_url, endpoint, "q")
        self.text = text if text is not None else endpoint
        self.status_code = status_code


class Agent:
    def __init__(self, app_name, url, apm_server):
        self.app_name = app_name
        self.url = url
        self.port = urlparse(url).port
        self.foo = Endpoint(self.url, "foo")
        self.bar = Endpoint(self.url, "bar")
        self.apm_server = apm_server
