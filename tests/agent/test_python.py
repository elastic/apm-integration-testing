import pytest
from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
@pytest.mark.flask
def test_req_flask(flask):
    utils.check_agent_transaction(flask.foo, flask.apm_server.elasticsearch, ct=2)


@pytest.mark.flask
def test_conc_req_flask(flask_gunicorn):
    foo = Concurrent.Endpoint(flask_gunicorn.foo.url,
                              flask_gunicorn.app_name,
                              [".*.foo"],
                              "GET /foo")
    Concurrent(flask_gunicorn.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.flask
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


@pytest.mark.version
@pytest.mark.django
def test_req_django(django):
    utils.check_agent_transaction(django.foo, django.apm_server.elasticsearch)


@pytest.mark.django
def test_conc_req_django(django):
    foo = Concurrent.Endpoint(django.foo.url,
                              django.app_name,
                              [".*.foo"],
                              "GET foo.views.show")
    Concurrent(django.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.django
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
