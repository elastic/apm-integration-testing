import pytest

from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
@pytest.mark.go_nethttp
def test_req_go_nethttp(go_nethttp):
    utils.check_agent_transaction(
        go_nethttp.foo, go_nethttp.apm_server.elasticsearch, ct=2)


@pytest.mark.version
@pytest.mark.go_nethttp
def test_concurrent_req_go_nethttp(go_nethttp):
    foo = Concurrent.Endpoint(go_nethttp.foo.url,
                              go_nethttp.app_name,
                              ["foo"],
                              "GET /foo")
    Concurrent(go_nethttp.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.version
@pytest.mark.go_nethttp
def test_concurrent_req_go_nethttp_foobar(go_nethttp):
    foo = Concurrent.Endpoint(go_nethttp.foo.url,
                              go_nethttp.app_name,
                              ["foo"],
                              "GET /foo",
                              events_no=375)
    bar = Concurrent.Endpoint(go_nethttp.bar.url,
                              go_nethttp.app_name,
                              ["bar", "extra"],
                              "GET /bar")
    Concurrent(go_nethttp.apm_server.elasticsearch, [foo, bar], iters=1).run()
