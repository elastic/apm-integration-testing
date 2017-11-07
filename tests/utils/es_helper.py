import time
import timeout_decorator


class ESHelper:
    def __init__(self, elasticsearch):
        self.elasticsearch = elasticsearch
        self.index = "apm-*"

    def clean(self):
        self.elasticsearch.indices.delete(self.index)

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
            s = self.elasticsearch.search(index=self.index,
                                          body={"query": {"match_all": {}}})
            ct = s['hits']['total']
        return s
