import elasticsearch
import time
import timeout_decorator


class Elasticsearch:
    def __init__(self, url):
        self.es = elasticsearch.Elasticsearch([url])
        self.index = "apm-*"

    def clean(self):
        self.es.indices.delete(self.index)
        self.es.indices.refresh()

    def verify_transaction_data(self, name=None):
        try:
            ct = self.fetch_all()['hits']['total']
        except timeout_decorator.TimeoutError:
            ct = 0
        assert ct == 2

    @timeout_decorator.timeout(10)
    def fetch_all(self):
        ct = 0
        s = {}
        while ct == 0:
            time.sleep(1)
            s = self.es.search(index=self.index,
                               body={"query": {"match_all": {}}})
            ct = s['hits']['total']
        return s
