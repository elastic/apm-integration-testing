import elasticsearch
import time
import timeout_decorator


class Elasticsearch(object):
    def __init__(self, url):
        self.es = elasticsearch.Elasticsearch([url])
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
