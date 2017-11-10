import requests
from timeout_decorator import TimeoutError


def test_request_express(elasticsearch, apm_server, express):
    check_transaction(express, elasticsearch)


def check_transaction(agent, elasticsearch):
    elasticsearch.clean()
    r = requests.get(agent.foo.url)
    assert r.text == agent.foo.text
    assert r.status_code == agent.foo.status_code

    try:
        q = {'query': {'term': {'processor.name': 'transaction'}}}
        ct = elasticsearch.fetch(q)['hits']['total']
    except TimeoutError:
        ct = 0
    assert ct == 2
