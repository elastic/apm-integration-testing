import pytest

from tests.endpoint import Endpoint
from tests.fixtures import default


@pytest.fixture(scope="session")
def apm_server(es):
    class APMServer:
        def __init__(self, url, elasticsearch):
            self.url = url
            self.elasticsearch = elasticsearch
            self.transaction_endpoint = Endpoint(self.url,
                                                 "v1/transactions",
                                                 qu_str=None,
                                                 text="",
                                                 status_code=202)

    return APMServer(default.from_env("APM_SERVER_URL"), es)
