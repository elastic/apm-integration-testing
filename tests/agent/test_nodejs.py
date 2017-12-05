import pytest
from tests.agent.concurrent_requests import Concurrent
from tests import utils


@pytest.mark.version
def test_request_express(express):
    utils.check_agent_transaction(
        express.foo, express.apm_server.elasticsearch)


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
