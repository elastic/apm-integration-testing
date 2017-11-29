import pytest
import os
import elasticsearch as es_wrapper
import timeout_decorator
import time


@pytest.fixture(scope="session")
def elasticsearch():
    class Elasticsearch(object):
        def __init__(self, url):
            self.es = es_wrapper.Elasticsearch([url])
            self.index = "apm-*"

        def clean(self):
            self.es.indices.delete(self.index)
            self.es.indices.refresh()

        def term_q(self, field, val):
            return {"query": {"term": {field: val}}}

        def regexp_q(self, field, r):
            return {"query": {"regexp": {field: r}}}

        @timeout_decorator.timeout(10)
        def fetch(self, q):
            ct = 0
            s = {}
            while ct == 0:
                time.sleep(1)
                s = self.es.search(index=self.index, body=q)
                ct = s['hits']['total']
            return s


    return Elasticsearch(os.environ["ES_URL"])
