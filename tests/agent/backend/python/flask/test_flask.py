from utils import agent
from utils.framework import Framework
# from io import BytesIO
# import os

APP_NAME = 'flask_app'
APP_PORT = '8001'
APP_URL = 'http://localhost:8001'
FOO = 'foo'


def test_http_request(apm_server, elasticsearch):
    __check_transaction(elasticsearch)


# def test_transaction_secured(apm_server_secured, elasticsearch):
    # __check_transaction(apm_server_secured.url, elasticsearch)


def test_with_threads(apm_server, elasticsearch):
    events_no = 1000
    iterations = 3




def __check_transaction(elasticsearch):
    ports = {"{}/tcp".format(APP_PORT): APP_PORT}
    path = "tests/agent/backend/python/flask"
    Framework(APP_NAME).start(ports=ports, path=path)

    elasticsearch.clean()
    url = "{}/{}".format(APP_URL, FOO)
    agent.send_and_verify_request(url, text=FOO)
    elasticsearch.verify_transaction_data(APP_NAME)
