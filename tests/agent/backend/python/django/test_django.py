from utils import framework
from utils import es
from utils import agent


def test_http_request(apm_server, elasticsearch):
    name = "django_app"
    ports = {'8002/tcp': 8002}
    path = "tests/agent/backend/python/django"
    framework.start_framework(name, path, ports)

    es.clean(elasticsearch)
    url = 'http://localhost:8002/foo'
    agent.send_and_verify_request(url, text="foo")
    es.verify_transaction_data(elasticsearch, name)
