from contextlib import contextmanager
import requests
import time
from urlparse import urljoin

from tests.fixtures import default


@contextmanager
def remote_config(url, sampling_rate=1.0):
    def data(sample_rate):
        return {
            "agent_name": "python",
            "service": {"name": default.from_env('FLASK_SERVICE_NAME')},
            "settings": {"transaction_sample_rate": sample_rate}
        }

    headers = {"Content-Type": "application/json", "kbn-xsrf": "1"}
    wait = 2.5  # just higher than apm-server.agent.config.cache.expiration

    try:
        r = requests.post(
            urljoin(url, "/api/apm/settings/agent-configuration/new"),
            headers=headers,
            json=data(sampling_rate),
        )
        r.raise_for_status()
        config_id = r.json()["_id"]
        time.sleep(wait)  # give enough time to agent to pick up the config

        yield config_id

    finally:
        # revert to original
        r2 = requests.put(
            urljoin(url, "/api/apm/settings/agent-configuration/" + config_id),
            headers=headers,
            json=data(1.0),
        )
        r2.raise_for_status()
        time.sleep(wait)

        r3 = requests.delete(
            urljoin(url, "/api/apm/settings/agent-configuration/" + config_id),
            headers=headers,
        )
        r3.raise_for_status()
        time.sleep(wait)
