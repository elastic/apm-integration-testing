from timeout_decorator import TimeoutError
import requests


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


def check_server_transaction(endpoint, elasticsearch, json, headers=None, ct=2):
    elasticsearch.clean()
    if headers is None:
        headers = {'Content-Type': 'application/json'}
    r = requests.post(endpoint.url, json=json, headers=headers)
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
        except TimeoutError:
            retries = max_retries
            actual = -1

    assert actual == expected, "Expected {}, queried {}".format(
        expected, actual)
