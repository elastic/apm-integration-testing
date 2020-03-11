from timeout_decorator import TimeoutError
from tests.fixtures import default
import requests
import time

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def check_agent_transaction(endpoint, elasticsearch, ct=2):
    elasticsearch.clean()
    r = requests.get(endpoint.url)
    check_request_response(r, endpoint)
    check_elasticsearch_count(elasticsearch, ct)


def check_agent_error(endpoint, elasticsearch, ct=1):
    elasticsearch.clean()
    r = requests.get(endpoint.url)
    assert r.status_code == endpoint.status_code
    check_elasticsearch_count(elasticsearch, ct, processor='error')


def check_server_transaction(endpoint, elasticsearch, payload, headers=None, ct=2):
    elasticsearch.clean()
    if headers is None:
        headers = {'Content-Type': 'application/x-ndjson'}
    headers['Authorization'] = 'Bearer {}'.format(default.from_env("ELASTIC_APM_SECRET_TOKEN"))
    r = requests.post(endpoint.url, data=payload, headers=headers, verify=False)
    check_request_response(r, endpoint)
    check_elasticsearch_count(elasticsearch, ct)


def check_request_response(req, endpoint):
    msg = "Expected {}, got {}".format(endpoint.text, req.text)
    assert req.text == endpoint.text, msg
    assert req.status_code == endpoint.status_code


def check_elasticsearch_count(elasticsearch,
                              expected,
                              processor='transaction',
                              query=None):
    if query is None:
        query = {'query': {'term': {'processor.name': processor}}}

    actual = 0
    retries = 0
    max_retries = 3
    while actual != expected and retries < max_retries:
        try:
            actual = elasticsearch.count(query)
            retries += 1
            time.sleep(10)
        except TimeoutError:
            retries += 1
            actual = -1

    assert actual == expected, "Expected {}, queried {}".format(
        expected, actual)


def getElasticsearchURL():
    es_url = default.from_env("ES_URL")
    es_user = default.from_env("ES_USER")
    es_pass = default.from_env("ES_PASS")
    url = urlparse(es_url)
    url = url._replace(netloc='{}:{}@{}'.format(es_user, es_pass, url.netloc))
    return url.geturl()
