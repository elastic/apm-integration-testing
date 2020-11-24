import json
from .service import Service
from .helpers import wget_healthcheck
from .opbeans import OpbeansService, OpbeansRum


class Toxi(Service):
    SERVICE_PORT = 8474
    opbeans_side_car = False

    def __init__(self):
        self.service_offset = 10000
        super().__init__()

    def _content(self):
        return dict(
            healthcheck=wget_healthcheck(8474, path="/proxies"),
            image="shopify/toxiproxy",
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT, expose=True)],
            volumes=["./docker/toxi/toxi.cfg:/toxi/toxi.cfg"],
            command=["-host=0.0.0.0", "-config=/toxi/toxi.cfg"]
        )

    def gen_config(self, services):
        config = []
        opbeans_sidecars = ['postgres', 'redis', 'opbeans-load-generator']
        opbeans_2nds = ('opbeans-go01', 'opbeans-java01', 'opbeans-python01', 'opbeans-ruby01', 'opbeans-dotnet01',
                        'opbeans-node01')
        for s in services:
            # TODO refactor this for DRY
            is_opbeans_service = isinstance(s, OpbeansService) or s is OpbeansRum
            is_opbeans_sidecar = s.name() in opbeans_sidecars
            is_opbeans_2nd = s.name() in opbeans_2nds
            if hasattr(s, "SERVICE_PORT") and not s.name().startswith('toxi') and (is_opbeans_service or is_opbeans_sidecar or is_opbeans_2nd):
                sp = int(s.SERVICE_PORT)
                service_def = {
                    "name": s.name(),
                    "listen": "[::]:{}".format(sp),
                    "upstream": "{}:{}".format(s.name(), sp),
                    "enabled": True
                }
                config.append(service_def)
        ret = json.dumps(config, sort_keys=True, indent=4)
        return ret
