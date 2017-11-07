import requests


def test_process_transaction(minimal, apm_server, elasticsearch, kibana):
    # TODO: url must be configurable
    url = "http://localhost:8200/v1/transactions"
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, json=minimal, headers=headers)
    assert r.text == ""
    assert r.status_code == 202
