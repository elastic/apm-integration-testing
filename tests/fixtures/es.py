import time

import elasticsearch
import pytest
import timeout_decorator

from tests.utils import getElasticsearchURL
from tests.fixtures import default


@pytest.fixture(scope="session")
def es():
    class Elasticsearch(object):
        def __init__(self, url):
            verify = default.from_env("PYTHONHTTPSVERIFY") == "1"
            self.es = elasticsearch.Elasticsearch(url,
                                                  verify_certs=verify,
                                                  connection_class=elasticsearch.RequestsHttpConnection)
            self.index = "apm-*"

        def clean(self):
            self.es.indices.delete(self.index)
            self.es.indices.refresh()

        def term_q(self, filters):
            clauses = []
            for field, value in filters:
                if isinstance(value, list):
                    clause = {"terms": {field: value}}
                else:
                    clause = {"term": {field: {"value": value}}}
                clauses.append(clause)
            return {"query": {"bool": {"must": clauses}}}

        @timeout_decorator.timeout(10)
        def count(self, q):
            ct = 0
            while ct == 0:
                time.sleep(3)
                s = self.es.count(index=self.index, body=q)
                ct = s['count']
            return ct

    return Elasticsearch(getElasticsearchURL())
