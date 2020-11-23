
from .service import Service


class Toxi(Service):
    SERVICE_PORT = 8474
    opbeans_side_car = False

    def _content(self):
        return dict(
            # environment=["POSTGRES_DB=opbeans", "POSTGRES_PASSWORD=verysecure"],
            # healthcheck={"interval": "10s", "test": ["CMD", "pg_isready", "-h", "postgres", "-U", "postgres"]},
            image="shopify/toxiproxy",
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT, expose=True)],
            # volumes=["./docker/opbeans/sql:/docker-entrypoint-initdb.d", "pgdata:/var/lib/postgresql/data"],
        )
