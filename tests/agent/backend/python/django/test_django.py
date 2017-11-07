from utils.framework import Framework
from utils import agent

APP_NAME = 'django_app'
APP_PORT = '8002'
APP_URL = 'http://localhost:8002'
FOO = 'foo'


def test_http_request(apm_server, elasticsearch):
    ports = {"{}/tcp".format(APP_PORT): APP_PORT}
    path = "tests/agent/backend/python/django"
    Framework(APP_NAME).start(ports=ports, path=path)

    elasticsearch.clean()
    url = "{}/{}".format(APP_URL, FOO)
    agent.send_and_verify_request(url, text=FOO)
    elasticsearch.verify_transaction_data(APP_NAME)
