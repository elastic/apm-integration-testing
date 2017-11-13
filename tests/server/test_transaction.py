import requests


def test_process_transaction(minimal, apm_server, kibana):
    url = "{}/v1/transactions".format(apm_server.url)
    headers = {'Content-Type': 'application/json'}
    r = requests.post(url, json=minimal, headers=headers)
    assert r.text == ""
    assert r.status_code == 202

    # TODO: check kibana
