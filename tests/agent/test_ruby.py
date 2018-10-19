import pytest

from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
def test_req_rails(rails):
    utils.check_agent_transaction(
        rails.foo, rails.apm_server.elasticsearch)


@pytest.mark.version
def test_rails_error(rails):
    utils.check_agent_error(
        rails.oof, rails.apm_server.elasticsearch)


@pytest.mark.version
def test_conc_req_rails(es, apm_server, rails):
    foo = Concurrent.Endpoint(rails.foo.url,
                              rails.app_name,
                              ["ApplicationController#foo"],
                              "ApplicationController#foo",
                              events_no=1000)
    Concurrent(es, [foo], iters=1).run()


@pytest.mark.version
def test_conc_req_rails_foobar(es, apm_server, rails):
    foo = Concurrent.Endpoint(rails.foo.url,
                              rails.app_name,
                              ["ApplicationController#foo"],
                              "ApplicationController#foo")
    bar = Concurrent.Endpoint(rails.bar.url,
                              rails.app_name,
                              ["ApplicationController#bar", "app.extra"],
                              "ApplicationController#bar",
                              events_no=820)
    Concurrent(es, [foo, bar], iters=1).run()
