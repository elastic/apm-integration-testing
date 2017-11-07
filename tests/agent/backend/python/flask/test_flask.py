from utils import framework
from utils import agent
from utils import es


def test_http_request(apm_server, elasticsearch):
    name = "flask_app"
    ports = {'8001/tcp': 8001}
    path = "tests/agent/backend/python/flask"
    framework.start_framework(name, path, ports)

    es.clean(elasticsearch)
    url = 'http://localhost:8001/foo'
    agent.send_and_verify_request(url, text="foo")
    es.verify_transaction_data(elasticsearch, name)
