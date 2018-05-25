import os

import pytest

from tests.fixtures import default


@pytest.fixture(scope="session")
def kibana(es):
    class Kibana:
        def __init__(self, url, es):
            self.url = url
            self.elasticsearch = es

    return Kibana(default.from_env("KIBANA_URL"), es)
