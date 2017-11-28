from tests import utils


def test_process_transaction(minimal, apm_server):
    utils.check_server_transaction(apm_server.transaction_endpoint,
                                   apm_server.elasticsearch,
                                   minimal,
                                   ct=1)
