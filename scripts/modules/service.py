import json

from abc import abstractmethod

from .helpers import resolve_bc, parse_version, _camel_hyphen

DEFAULT_STACK_VERSION = "8.0"
DEFAULT_APM_SERVER_URL = "http://apm-server:8200"
DEFAULT_APM_JS_SERVER_URL = "http://localhost:8200"
DEFAULT_SERVICE_VERSION = "9c2e41c8-fb2f-4b75-a89d-5089fb55fc64"


class Service(object):
    """encapsulate docker-compose service definition"""

    DEFAULT_ELASTICSEARCH_HOSTS = "elasticsearch:9200"
    DEFAULT_KIBANA_HOST = "kibana:5601"

    # is this a side car service for opbeans. If yes, it will automatically
    # start if any opbeans service starts
    opbeans_side_car = False

    def __init__(self, **options):
        self.options = options

        if not hasattr(self, "docker_registry"):
            self.docker_registry = "docker.elastic.co"
        if not hasattr(self, "docker_name"):
            self.docker_name = self.name()
        if not hasattr(self, "docker_path"):
            self.docker_path = self.name()

        if hasattr(self, "SERVICE_PORT"):
            self.port = options.get(self.option_name() + "_port", self.SERVICE_PORT)

        self._oss = options.get(self.option_name() + "_oss") or options.get("oss")
        self._release = options.get(self.option_name() + "_release") or options.get("release")
        self._snapshot = options.get(self.option_name() + "_snapshot") or options.get("snapshot")

        # version is service specific or stack or default
        self._version = options.get(self.option_name() + "_version") or options.get("version", DEFAULT_STACK_VERSION)

        # bc depends on version for resolution
        if not self.option_name().startswith("opbeans"):
            self._bc = resolve_bc(self._version, options.get(self.option_name() + "_bc") or options.get("bc"))
        else:
            self._bc = ""

        self.depends_on = {}

        self.env_file = []

    @property
    def bc(self):
        return self._bc

    def default_container_name(self):
        return "_".join(("localtesting", self.version, self.name()))

    def default_image(self, version_override=None):
        """default container image path constructor"""
        image = "/".join((self.docker_registry, self.docker_path, self.docker_name))
        if self.oss:
            image += "-oss"
        image += ":" + (version_override or self.version)
        # no command line option for setting snapshot, snapshot == no bc and not release
        if self.snapshot or not (any((self.bc, self.release))):
            image += "-SNAPSHOT"
        return image

    def default_labels(self):
        return ["co.elastic.apm.stack-version=" + self.version]

    @staticmethod
    def default_logging():
        return {
            "driver": "json-file",
            "options": {
                "max-file": "5",
                "max-size": "2m"
            }
        }

    @staticmethod
    def enabled():
        return False

    def at_least_version(self, target):
        return parse_version(self.version) >= parse_version(target)

    @classmethod
    def name(cls):
        return _camel_hyphen(cls.__name__).lower()

    @classmethod
    def option_name(cls):
        return cls.name().replace("-", "_")

    @property
    def oss(self):
        return self._oss

    @staticmethod
    def publish_port(external, internal=None, expose=False):
        addr = "" if expose else "127.0.0.1:"
        if internal is None:
            internal = external
        return addr + ":".join((str(external), str(internal)))

    @property
    def release(self):
        return self._release

    @property
    def snapshot(self):
        return self._snapshot

    def render(self):
        content = self._content()
        content.update(dict(
            container_name=content.get("container_name", self.default_container_name()),
            image=content.get("image", self.default_image()),
            labels=content.get("labels", self.default_labels()),
            logging=content.get("logging", self.default_logging())
        ))
        for prune in "image", "labels", "logging":
            if content[prune] is None:
                del (content[prune])

        return {self.name(): content}

    @property
    def version(self):
        return self._version

    @classmethod
    def add_arguments(cls, parser):
        """add service-specific command line arguments"""
        # allow port overrides
        if hasattr(cls, 'SERVICE_PORT'):
            parser.add_argument(
                '--' + cls.name() + '-port',
                type=int,
                default=cls.SERVICE_PORT,
                dest=cls.option_name() + '_port',
                help="service port"
            )

    def image_download_url(self):
        pass

    @abstractmethod
    def _content(self):
        pass


class StackService(object):
    """Mix in for Elastic services that have public docker images built but not available in a registry [yet]"""

    def build_candidate_manifest(self):
        version = self.version
        image = self.docker_name
        if self.oss:
            image += "-oss"
        key = "{image}-{version}-docker-image.tar.gz".format(
            image=image,
            version=version,
        )
        try:
            return self.bc["projects"][self.docker_name]["packages"][key]
        except KeyError:
            # help debug manifest issues
            print(json.dumps(self.bc))
            raise

    def image_download_url(self):
        # Elastic releases are public
        if self.release or not self.bc:
            return

        info = self.build_candidate_manifest()
        assert info["type"] == "docker"
        return info["url"]

    @classmethod
    def add_arguments(cls, parser):
        super(StackService, cls).add_arguments(parser)
        for image_detail_key in ("bc", "version"):
            parser.add_argument(
                "--" + cls.name() + "-" + image_detail_key,
                type=str,
                dest=cls.option_name() + "_" + image_detail_key,
                help="stack {} override".format(image_detail_key),
            )
        for image_detail_key in ("oss", "release", "snapshot"):
            parser.add_argument(
                "--" + cls.name() + "-" + image_detail_key,
                action="store_true",
                dest=cls.option_name() + "_" + image_detail_key,
                help="stack {} override".format(image_detail_key),
            )
