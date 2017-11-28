import pytest
import os
from tests.endpoint import Endpoint


@pytest.fixture(scope="session")
def apm_server(elasticsearch):
    class APMServer:
        def __init__(self, url, elasticsearch):
            self.url = url
            self.elasticsearch = elasticsearch
            self.transaction_endpoint = Endpoint(self.url,
                                                 "v1/transactions",
                                                 qu_str=None,
                                                 text="",
                                                 status_code=202)

    return APMServer(os.environ['APM_SERVER_URL'], elasticsearch)
