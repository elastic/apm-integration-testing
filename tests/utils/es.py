import time
import timeout_decorator


APM_INDEX = "apm-*"


def clean(elasticsearch):
    elasticsearch.indices.delete(APM_INDEX)


@timeout_decorator.timeout(10)
def fetch_all(elasticsearch):
    ct = 0
    s = {}
    while ct == 0:
        time.sleep(1)
        s = elasticsearch.search(index=APM_INDEX,
                                 body={"query": {"match_all": {}}})
        ct = s['hits']['total']
    return s


def verify_transaction_data(elasticsearch, name):
    try:
        ct = fetch_all(elasticsearch)['hits']['total']
    except timeout_decorator.TimeoutError:
        ct = 0
    assert ct == 2
