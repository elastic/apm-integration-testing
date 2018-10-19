import pytest
from tests.agent.concurrent_requests import Concurrent
from tests import utils


@pytest.mark.version
def test_request_express(express):
    utils.check_agent_transaction(
        express.foo, express.apm_server.elasticsearch)


@pytest.mark.skip(reason="need agent dev input")
@pytest.mark.version
def test_express_error(express):
    utils.check_agent_error(
        express.oof, express.apm_server.elasticsearch)


def test_conc_req_express(es, apm_server, express):
    foo = Concurrent.Endpoint(express.foo.url,
                              express.app_name,
                              ["app.foo"],
                              "GET /foo",
                              events_no=1000)
    Concurrent(es, [foo], iters=1).run()


def test_conc_req_node_foobar(es, apm_server, express):
    foo = Concurrent.Endpoint(express.foo.url,
                              express.app_name,
                              ["app.foo"],
                              "GET /foo")
    bar = Concurrent.Endpoint(express.bar.url,
                              express.app_name,
                              ["app.bar", "app.extra"],
                              "GET /bar",
                              events_no=820)
    Concurrent(es, [foo, bar], iters=1).run()
