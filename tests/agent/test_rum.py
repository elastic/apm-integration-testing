from tests.endpoint import Endpoint
from tests import utils
import requests


def test_rum(rum):
    elasticsearch = rum.apm_server.elasticsearch
    elasticsearch.clean()
    endpoint = Endpoint(rum.url, "run_integration_test")

    r = requests.get(endpoint.url)
    assert r.status_code == 200
    utils.check_elasticsearch_transaction(elasticsearch, 1, {'query': {'term': {'processor.event': 'transaction'}}})
