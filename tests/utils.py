import requests
from timeout_decorator import TimeoutError
import time


def check_agent_transaction(endpoint, elasticsearch, ct=2):
    elasticsearch.clean()
    r = requests.get(endpoint.url)
    check_request_response(r, endpoint)
    check_elasticsearch_transaction(elasticsearch, ct)


def check_server_transaction(endpoint, elasticsearch, json, headers=None, ct=2):
    elasticsearch.clean()
    if headers is None:
        headers = {'Content-Type': 'application/json'}
    r = requests.post(endpoint.url, json=json, headers=headers)
    check_request_response(r, endpoint)
    check_elasticsearch_transaction(elasticsearch, ct)


def check_request_response(req, endpoint):
    msg = "Expected {}, got {}".format(endpoint.text, req.text)
    assert req.text == endpoint.text, msg
    assert req.status_code == endpoint.status_code


def check_elasticsearch_transaction(elasticsearch, expected_count):
    q = {'query': {'term': {'processor.name': 'transaction'}}}
    actual_count = 0
    retries = 0
    max_retries = 3
    while actual_count != expected_count and retries < max_retries:
        try:
            actual_count = elasticsearch.fetch(q)['hits']['total']
            retries += 1
        except TimeoutError:
            retries = max_retries
            actual_count = -1

    assert actual_count == expected_count, "Expected {}, queried {}".format(
        expected_count, actual_count)
