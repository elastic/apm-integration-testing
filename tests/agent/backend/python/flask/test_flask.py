from utils import framework
from utils import agent
from utils.es_helper import ESHelper
from utils.framework import Framework
# from io import BytesIO
# import os

APP_NAME = 'flask_app'
APP_PORT = '8001'
APP_URL = 'http://localhost:8001'
FOO = 'foo'

# dir_path = os.path.dirname(os.path.realpath(__file__))
# docker = BytesIO('''
    # FROM python:3
    # RUN mkdir -p /app
    # WORKDIR /app
    # COPY . /app
    # '''.encode('utf-8'))


def test_http_request(apm_server, elasticsearch):
    __check_transaction(elasticsearch)


# def test_transaction_secured(apm_server_secured, elasticsearch):
    # __check_transaction(apm_server_secured.url, elasticsearch)


def __check_transaction(elasticsearch):
    ports = {"{}/tcp".format(APP_PORT): APP_PORT}
    path = "tests/agent/backend/python/flask"
    Framework(APP_NAME).start(ports=ports, path=path)

    es = ESHelper(elasticsearch)
    es.clean()
    url = "{}/{}".format(APP_URL, FOO)
    agent.send_and_verify_request(url, text=FOO)
    es.verify_transaction_data(APP_NAME)
