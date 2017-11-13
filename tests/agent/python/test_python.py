import requests
from timeout_decorator import TimeoutError
from agent.concurrent_requests import Concurrent


def test_req_flask(flask):
    check_transaction(flask, flask.apm_server.elasticsearch)


def test_conc_req_flask(flask_gunicorn):
    foo = Concurrent.Endpoint(flask_gunicorn.foo.url,
                              flask_gunicorn.app_name,
                              [".*.foo"],
                              "GET /foo")
    Concurrent(flask_gunicorn.apm_server.elasticsearch, [foo], iters=2).run()


def test_conc_req_flask_foobar(flask_gunicorn):
    foo = Concurrent.Endpoint(flask_gunicorn.foo.url,
                              flask_gunicorn.app_name,
                              [".*.foo"],
                              "GET /foo",
                              events_no=375)
    bar = Concurrent.Endpoint(flask_gunicorn.bar.url,
                              flask_gunicorn.app_name,
                              [".*.bar", ".*.extra"],
                              "GET /bar")
    Concurrent(flask_gunicorn.apm_server.elasticsearch, [foo, bar], iters=1).run()


def test_req_django(django):
    check_transaction(django, django.apm_server.elasticsearch)


def test_conc_req_django(django):
    foo = Concurrent.Endpoint(django.foo.url,
                              django.app_name,
                              [".*.foo"],
                              "GET foo.views.show")
    Concurrent(django.apm_server.elasticsearch, [foo], iters=2).run()


def test_conc_req_django_foobar(django):
    foo = Concurrent.Endpoint(django.foo.url,
                              django.app_name,
                              [".*.foo"],
                              "GET foo.views.show")
    bar = Concurrent.Endpoint(django.bar.url,
                              django.app_name,
                              [".*.bar", ".*.extra"],
                              "GET bar.views.show",
                              events_no=820)
    Concurrent(django.apm_server.elasticsearch, [foo, bar], iters=1).run()


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
