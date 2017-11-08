import requests
from timeout_decorator import TimeoutError
from agent.concurrent_requests import Concurrent


def test_req_flask(elasticsearch, apm_server, flask):
    check_transaction(flask, elasticsearch)


def test_conc_req_flask(elasticsearch, apm_server, flask):
    foo = Concurrent.Endpoint(flask.foo.url,
                              flask.app_name,
                              [".*.foo"],
                              "GET /foo")
    Concurrent(elasticsearch, [foo], iters=2).run()


def test_conc_req_flask_foobar(elasticsearch, apm_server, flask):
    foo = Concurrent.Endpoint(flask.foo.url,
                              flask.app_name,
                              [".*.foo"],
                              "GET /foo")
    bar = Concurrent.Endpoint(flask.bar.url,
                              flask.app_name,
                              [".*.bar", ".*.extra"],
                              "GET /bar")
    Concurrent(elasticsearch, [foo, bar], iters=1).run()


# def test_req_django(elasticsearch, apm_server, django):
    # check_transaction(django, elasticsearch)


# def test_conc_req_django(elasticsearch, apm_server, django):
    # foo = Concurrent.Endpoint(django.foo.url,
                              # django.app_name,
                              # [".*.foo"],
                              # "GET /foo")
    # Concurrent(elasticsearch, [foo], iters=2).run()


# def test_conc_req_django_foobar(elasticsearch, apm_server, django):
    # foo = Concurrent.Endpoint(django.foo.url,
                              # django.app_name,
                              # [".*.foo"],
                              # "GET /foo")
    # bar = Concurrent.Endpoint(django.bar.url,
                              # django.app_name,
                              # [".*.bar", ".*.extra"],
                              # "GET /bar")
    # Concurrent(elasticsearch, [foo, bar], iters=1).run()


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
