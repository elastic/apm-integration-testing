import pytest


@pytest.fixture
def minimal():
    return b"""{"metadata":{"service":{"name":"service1","agent":{"name":"python","version":"1.0"}}}}
{"transaction":{"id":"945254c567a5417e","name":"GET /api/types","type":"request","duration":32.592981,"result":"success","timestamp":1494342245999999,"trace_id":"945254c567a5417eaaaaaaaaaaaaaaaa","span_count":{"started":0}}}"""  # noqa: 501
