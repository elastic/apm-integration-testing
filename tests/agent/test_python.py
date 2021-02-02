import pytest

from tests import utils, agent
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
@pytest.mark.flask
def test_req_flask(flask):
    utils.check_agent_transaction(flask.foo, flask.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.flask
def test_flask_error(flask):
    utils.check_agent_error(flask.oof, flask.apm_server.elasticsearch, ct=1)


@pytest.mark.version
@pytest.mark.flask
def test_concurrent_req_flask(flask):
    foo = Concurrent.Endpoint(flask.foo.url,
                              flask.app_name,
                              ["app.foo"],
                              "GET /foo")
    Concurrent(flask.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.skip(reason="very unstable on CI, maybe due to many Gunicorn workers")
@pytest.mark.version
@pytest.mark.flask
def test_req_flask_agent_config(flask, kibana):
    # when re-added, remove the 'release;4.2' entry from python.yml
    # and verify that the Kibana request in the remote_config context manager is current
    with agent.remote_config(kibana.url, sampling_rate=0.0):
        # 1 transaction, 0 spans
        utils.check_agent_transaction(
            flask.foo, flask.apm_server.elasticsearch, ct=1)


@pytest.mark.version
@pytest.mark.flask
def test_concurrent_req_flask_foobar(flask):
    foo = Concurrent.Endpoint(flask.foo.url,
                              flask.app_name,
                              ["app.foo"],
                              "GET /foo",
                              events_no=375)
    bar = Concurrent.Endpoint(flask.bar.url,
                              flask.app_name,
                              ["app.bar", "app.extra"],
                              "GET /bar")
    Concurrent(flask.apm_server.elasticsearch, [foo, bar], iters=1).run()


@pytest.mark.version
@pytest.mark.django
def test_req_django(django):
    utils.check_agent_transaction(django.foo, django.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.django
def test_django_error(django):
    utils.check_agent_error(django.oof, django.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.django
def test_concurrent_req_django(django):
    foo = Concurrent.Endpoint(django.foo.url,
                              django.app_name,
                              ["foo.views.foo"],
                              "GET foo.views.show")
    Concurrent(django.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.version
@pytest.mark.django
def test_concurrent_req_django_foobar(django):
    foo = Concurrent.Endpoint(django.foo.url,
                              django.app_name,
                              ["foo.views.foo"],
                              "GET foo.views.show")
    bar = Concurrent.Endpoint(django.bar.url,
                              django.app_name,
                              ["bar.views.bar", "bar.views.extra"],
                              "GET bar.views.show",
                              events_no=820)
    Concurrent(django.apm_server.elasticsearch, [foo, bar], iters=1).run()
