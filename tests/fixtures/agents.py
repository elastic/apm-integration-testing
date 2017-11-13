import pytest
from fixtures.setup import utils
import subprocess
import os
from urllib.parse import urlparse
import timeout_decorator


@timeout_decorator.timeout(250)
@pytest.fixture(scope="session")
def flask(apm_server):
    os.environ['FLASK_APP_NAME'] = "flask_app"
    os.environ['FLASK_PORT'] = "8001"
    script = "tests/fixtures/setup/python/flask/start.sh"
    subprocess.call([script])
    url = "http://localhost:{}".format(os.environ['FLASK_PORT'])
    wait_until_setup(url, apm_server)
    return Agent(os.environ['FLASK_APP_NAME'], url, apm_server)


@timeout_decorator.timeout(250)
@pytest.fixture(scope="session")
def flask_gunicorn(apm_server):
    os.environ['PY_SERVER'] = 'GUNICORN'
    os.environ['FLASK_APP_NAME'] = "flask_gunicorn_app"
    os.environ['FLASK_PORT'] = "8002"
    script = "tests/fixtures/setup/python/flask/start.sh"
    subprocess.call([script])
    url = "http://localhost:{}".format(os.environ['FLASK_PORT'])
    wait_until_setup(url, apm_server)
    return Agent(os.environ['FLASK_APP_NAME'], url, apm_server)


@timeout_decorator.timeout(250)
@pytest.fixture(scope="session")
def django(apm_server):
    os.environ['DJANGO_APP_NAME'] = "django_app"
    os.environ['DJANGO_PORT'] = "8003"
    script = "tests/fixtures/setup/python/django/start.sh"
    subprocess.call([script])
    url = "http://localhost:{}".format(os.environ['DJANGO_PORT'])
    wait_until_setup("{}/foo".format(url), apm_server)
    return Agent(os.environ['DJANGO_APP_NAME'], url, apm_server)


@timeout_decorator.timeout(250)
@pytest.fixture(scope="session")
def express(apm_server):
    os.environ['EXPRESS_APP_NAME'] = "express_app"
    os.environ['EXPRESS_PORT'] = "8010"
    script = "tests/fixtures/setup/nodejs/express/start.sh"
    subprocess.call([script])
    url = "http://localhost:{}".format(os.environ['EXPRESS_PORT'])
    wait_until_setup(url, apm_server)
    return Agent(os.environ['EXPRESS_APP_NAME'], url, apm_server)


def wait_until_setup(url, apm_server):
    utils.wait_until_service_responding(url)
    apm_server.elasticsearch.clean()
    apm_server.elasticsearch.fetch({'query': {'match_all': {}}})


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
