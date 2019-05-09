import pytest

from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
@pytest.mark.dotnet
def test_req_dotnet(dotnet):
    utils.check_agent_transaction(
        dotnet.foo, dotnet.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.dotnet
def test_dotnet_error(dotnet):
    utils.check_agent_error(
        dotnet.oof, dotnet.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.dotnet
def test_concurrent_req_dotnet(dotnet):
    foo = Concurrent.Endpoint(dotnet.foo.url,
                              dotnet.app_name,
                              ["foo"],
                              "GET /foo")
    Concurrent(dotnet.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.version
@pytest.mark.dotnet
def test_concurrent_req_dotnet_foobar(dotnet):
    foo = Concurrent.Endpoint(dotnet.foo.url,
                              dotnet.app_name,
                              ["foo"],
                              "GET /foo",
                              events_no=375)
    bar = Concurrent.Endpoint(dotnet.bar.url,
                              dotnet.app_name,
                              ["bar", "extra"],
                              "GET /bar")
    Concurrent(dotnet.apm_server.elasticsearch, [foo, bar], iters=1).run()
