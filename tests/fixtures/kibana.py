import os

import pytest


@pytest.fixture(scope="session")
def kibana(es):
    class Kibana:
        def __init__(self, url, es):
            self.url = url
            self.elasticsearch = es

    return Kibana(os.environ["KIBANA_URL"], es)
