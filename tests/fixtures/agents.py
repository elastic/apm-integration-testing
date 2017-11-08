import pytest
from fixtures.setup import docker_helper


# TODO: use ENV_VARIABLE for agent configs

@pytest.fixture(scope="module")
def flask():
    class Flask:
        def __init__(self):
            self.app_name = 'flask_app'
            self.port = '8001'
            self.url = 'http://localhost:8001'
            self.foo = Endpoint(self.url, "foo")
            self.bar = Endpoint(self.url, "bar")
            ports = {"{}/tcp".format(self.port): self.port}
            path = "tests/agent/python/flask"
            container = start_container(self.app_name, ports, path)

    return Flask()


@pytest.fixture(scope="module")
def django():
    class Django:
        def __init__(self):
            self.app_name = 'django_app'
            self.port = '8002'
            self.url = 'http://localhost:8002'
            self.foo = Endpoint(self.url, "foo")
            self.bar = Endpoint(self.url, "bar")
            ports = {"{}/tcp".format(self.port): self.port}
            path = "tests/agent/python/django"
            container = start_container(self.app_name, ports, path)
    return Django()


@pytest.fixture(scope="module")
def express():
    class Express:
        def __init__(self):
            self.app_name = 'express_app'
            self.port = '8010'
            self.url = 'http://localhost:8010'
            self.foo = Endpoint(self.url, "foo")
            self.bar = Endpoint(self.url, "bar")
            ports = {"{}/tcp".format(self.port): self.port}
            path = "tests/agent/nodejs/express"
            container = start_container(self.app_name, ports, path)
    return Express()


def url(base_url, u, qs=None):
    url = "{}/{}".format(base_url, u)
    if qs is not None:
        url = "{}?{}".format(url, qs)
    return url


def start_container(name, ports, path):
    docker_helper.build_image(name, path)
    return docker_helper.run_container(name, ports=ports)

class Endpoint:
    def __init__(self, base_url, endpoint, text=None, status_code=200):
        self.url = url(base_url, endpoint, "q")
        self.text = text if text is not None else endpoint
        self.status_code = status_code
