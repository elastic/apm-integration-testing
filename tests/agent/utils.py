import requests
from timeout_decorator import TimeoutError


def check_transaction(agent, elasticsearch, ct=2):
    elasticsearch.clean()
    r = requests.get(agent.foo.url)
    assert r.text == agent.foo.text, "Expected {}, got {}".format(r.text, agent.foo.text)
    assert r.status_code == agent.foo.status_code

    q = {'query': {'term': {'processor.name': 'transaction'}}}
    es_ct = ct-1
    retries = 0
    while es_ct != ct and retries < 2:
        try:
            es_ct = elasticsearch.fetch(q)['hits']['total']
            retries += 1
        except TimeoutError:
            es_ct = 0
    assert es_ct == ct, "Expected {}, queried {}".format(ct, es_ct)
