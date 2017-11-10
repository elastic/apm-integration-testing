import requests
from timeout_decorator import TimeoutError
from agent.concurrent_requests import Concurrent


def test_request_express(elasticsearch, apm_server, express):
    check_transaction(express, elasticsearch)


def test_conc_req_express(elasticsearch, apm_server, express):
    foo = Concurrent.Endpoint(express.foo.url,
                              express.app_name,
                              [".*.foo"],
                              "GET /foo",
                              events_no=1000)
    Concurrent(elasticsearch, [foo], iters=1).run()


def test_conc_req_node_foobar(elasticsearch, apm_server, express):
    foo = Concurrent.Endpoint(express.foo.url,
                              express.app_name,
                              [".*.foo"],
                              "GET /foo")
    bar = Concurrent.Endpoint(express.bar.url,
                              express.app_name,
                              [".*.bar", ".*.extra"],
                              "GET /bar",
                              events_no=820)
    Concurrent(elasticsearch, [foo, bar], iters=1).run()


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
