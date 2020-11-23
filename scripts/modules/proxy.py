import json
from .service import Service
from .helpers import curl_healthcheck


class Toxi(Service):
    SERVICE_PORT = 8474
    opbeans_side_car = False

    def __init__(self):
        self.service_offset = 10000
        super().__init__()

    def _content(self):
        return dict(
            # environment=["POSTGRES_DB=opbeans", "POSTGRES_PASSWORD=verysecure"],
            healthcheck=curl_healthcheck(8474, "localhost", path="/proxies"),
            image="shopify/toxiproxy",
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT, expose=True)],
            volumes=["./docker/toxi/toxi.cfg:/toxi/toxi.cfg"],
            # TODO We need to override command: to add the config flag here
            command=["-host=0.0.0.0", "-config=/toxi/toxi.cfg"]
        )

    def gen_config(self, services):
        config = []
        for s in services:
            if hasattr(s, "SERVICE_PORT"):
                sp = int(s.SERVICE_PORT)
                service_def = {
                    "name": s.name(),
                    "listen": "[::]:{}".format(self.service_offset + sp),
                    "upstream": "{}:{}".format(s.name(), sp),
                    "enabled": True
                }
                config.append(service_def)
        ret = json.dumps(config, sort_keys=True, indent=4)
        return ret
