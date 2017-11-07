import requests


def send_and_verify_request(url, text="OK", status_code=200):
    r = requests.get(url)
    assert r.text == text
    assert r.status_code == status_code
