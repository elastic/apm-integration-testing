import os
import json
from .service import Service
from .helpers import wget_healthcheck
from .opbeans import OpbeansService, OpbeansRum


class Dyno(Service):
    """
    Dyno is the management interface for the
    proxy services
    """
    SERVICE_PORT = 9999
    opbeans_side_car = False

    def __init__(self):
        super().__init__()

    def _resolve_docker_sock(self):
        """
        On some operating systems, like OS X, the docker socket is actually symlinked
        from /var/run and so we need to give the real source to our volume or we won't
        be able to resolve it from inside the container runtime
        """
        known_sock = '/var/run/docker.sock'
        if os.path.islink(known_sock):
            return os.readlink(known_sock)
        else:
            return known_sock

    def _content(self):
        return dict(
            build=dict(
                context="docker/dyno",
                dockerfile="Dockerfile",
                args=[]
            ),
            environment={"TOXI_HOST": "toxi", "TOXI_PORT": "8474"},
            container_name="dyno",
            image=None,
            labels=None,
            logging=None,
            healthcheck=wget_healthcheck(8000, path="/"),
            ports=["9000:8000"],
            volumes=["{}:/var/run/docker.sock".format(self._resolve_docker_sock())],
        )

class Toxi(Service):
    SERVICE_PORT = 8474
    opbeans_side_car = False

    def __init__(self):
        self.service_offset = 10000
        super().__init__()
        self.generated_ports = [self.publish_port(self.port, self.SERVICE_PORT, expose=True)]

    def _content(self):
        return dict(
            healthcheck=wget_healthcheck(8474, path="/proxies"),
            image="shopify/toxiproxy",
            labels=None,
            ports=self.generated_ports,
            volumes=["./docker/toxi/toxi.cfg:/toxi/toxi.cfg"],
            command=["-host=0.0.0.0", "-config=/toxi/toxi.cfg"]
        )

    def gen_ports(self, services):
        """
        Take the services we know about and look for user-facing
        instances and be sure to expose them from our container
        """
        for s in services:
            if isinstance(s, OpbeansService) or s is OpbeansRum:  # is opbeans service
                self.generated_ports.append("{}:{}".format(s.SERVICE_PORT, s.SERVICE_PORT))

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

            if hasattr(s, "SERVICE_PORT") and not s.name().startswith('toxi') and \
                    (is_opbeans_service or is_opbeans_sidecar or is_opbeans_2nd):

                sp = int(s.SERVICE_PORT)
                if is_opbeans_service:
                    # We use APPLICATION_PORT because we want the container port and not the exposed port
                    upstream_port = s.APPLICATION_PORT
                else:
                    upstream_port = sp

                service_def = {
                    "name": s.name(),
                    "listen": "[::]:{}".format(sp),
                    "upstream": "{}:{}".format(s.name(), upstream_port),
                    "enabled": True
                }
                config.append(service_def)
        ret = json.dumps(config, sort_keys=True, indent=4)
        return ret
