import pytest

from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.java_spring
def test_req_java_spring(java_spring):
    utils.check_agent_transaction(
        java_spring.foo, java_spring.apm_server.elasticsearch)


@pytest.mark.java_spring
def test_java_spring_error(java_spring):
    utils.check_agent_error(
        java_spring.oof, java_spring.apm_server.elasticsearch)


@pytest.mark.java_spring
def test_concurrent_req_java_spring(java_spring):
    foo = Concurrent.Endpoint(java_spring.foo.url,
                              java_spring.app_name,
                              ["foo"],
                              "GreetingController#foo")
    Concurrent(java_spring.apm_server.elasticsearch, [foo], iters=2).run()


@pytest.mark.java_spring
def test_concurrent_req_java_spring_foobar(java_spring):
    foo = Concurrent.Endpoint(java_spring.foo.url,
                              java_spring.app_name,
                              ["foo"],
                              "GreetingController#foo",
                              events_no=375)
    bar = Concurrent.Endpoint(java_spring.bar.url,
                              java_spring.app_name,
                              ["bar", "extra"],
                              "GreetingController#bar")
    Concurrent(java_spring.apm_server.elasticsearch, [foo, bar], iters=1).run()
