import pytest

from tests import utils
from tests.agent.concurrent_requests import Concurrent


@pytest.mark.version
@pytest.mark.php_apache
def test_req_php_apache(php_apache):
    utils.check_agent_transaction(
        php_apache.foo, php_apache.apm_server.elasticsearch)


@pytest.mark.version
@pytest.mark.php_apache
def test_concurrent_req_php_apache(php_apache):
    foo = Concurrent.Endpoint(php_apache.foo.url,
                              php_apache.app_name,
                              ["foo"],
                              "GET /foo/?q=1")
    Concurrent(php_apache.apm_server.elasticsearch, [foo], iters=2).run()
