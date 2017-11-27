import requests
from timeout_decorator import TimeoutError


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


def check_elasticsearch_transaction(elasticsearch, ct=2):
    q = {'query': {'term': {'processor.name': 'transaction'}}}
    es_ct = ct-1
    retries = 0
    while es_ct != ct and retries < 2:
        try:
            es_ct = elasticsearch.fetch(q)['hits']['total']
            retries += 1
        except TimeoutError:
            es_ct = 0
    assert es_ct == ct, "Expected {}, queried {}".format(ct, es_ct)
