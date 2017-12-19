import os

import pytest


@pytest.fixture(scope="session")
def kibana(elasticsearch):
    class Kibana:
        def __init__(self, url, elasticsearch):
            self.url = url
            self.elasticsearch = elasticsearch

    return Kibana(os.environ["KIBANA_URL"], elasticsearch)
