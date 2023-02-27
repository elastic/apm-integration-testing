import collections
import collections.abc
import json
import sys

from abc import abstractmethod

from .helpers import resolve_bc, parse_version, _camel_hyphen

DEFAULT_STACK_VERSION = "8.0"
DEFAULT_APM_SERVER_URL = "http://apm-server:8200"
DEFAULT_APM_JS_SERVER_URL = "http://localhost:8200"
DEFAULT_APM_LOG_LEVEL = "info"
DEFAULT_SERVICE_VERSION = "9c2e41c8-fb2f-4b75-a89d-5089fb55fc64"


class Service(object):
    """encapsulate docker-compose service definition"""

    DEFAULT_KIBANA_HOST = "kibana:5601"
    DEFAULT_ELASTICSEARCH_HOST = "elasticsearch:9200"
    DEFAULT_ELASTICSEARCH_HOSTS_NO_TLS = "http://" + DEFAULT_ELASTICSEARCH_HOST
    DEFAULT_ELASTICSEARCH_HOSTS_TLS = "https://" + DEFAULT_ELASTICSEARCH_HOST
    DEFAULT_KIBANA_HOST_TLS = "https://" + DEFAULT_KIBANA_HOST
    DEFAULT_KIBANA_HOST_NO_TLS = "http://" + DEFAULT_KIBANA_HOST
    SERVICE_TOKEN = "AAEAAWVsYXN0aWMvZmxlZXQtc2VydmVyL2VsYXN0aWMtcGFja2FnZS1mbGVldC1zZXJ2ZXItdG9rZW46bmgtcFhoQzRRQ2FXbms2U0JySGlWQQ"  # noqa

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
        self._ubi8 = options.get(self.option_name() + "_ubi8") or options.get("ubi8")

        # version is service specific or stack or default
        self._version = options.get(self.option_name() + "_version") or options.get("version", DEFAULT_STACK_VERSION)

        # bc depends on version for resolution
        if not self.option_name().startswith("opbeans"):
            self._bc = resolve_bc(self._version, options.get(self.option_name() + "_bc") or options.get("bc"))
        else:
            self._bc = ""

        self.depends_on = {}

        self.apm_api_key = {}
        if self.options.get("elastic_apm_api_key"):
            if self.at_least_version("7.6"):
                self.apm_api_key = {"ELASTIC_APM_API_KEY": options.get("elastic_apm_api_key")}
            else:
                print('WARNING: elastic_apm_api_key is not supported for the current version. Use version +7.6.')
        if self._oss and self.name() in ("elasticsearch", "kibana"):
            if self.at_least_version("7.11") or (self.at_least_version("6.8.14") and self.version_lower_than("6.9")):
                print('ERROR: OSS distribution is ONLY supported in 7.11+/6.8.14+ for Kibana and Elasticsearch.')
                sys.exit(1)

        self._es_tls = options.get("elasticsearch_enable_tls", False)
        self._kibana_tls = options.get("kibana_enable_tls", False)
        self._env_vars = options.get(self.option_name() + "_env_vars", [])

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
        if self.ubi8:
            image += "-ubi8"
        image += ":" + (version_override or self.version)
        # no command line option for setting snapshot, snapshot == no bc and not release
        if self.snapshot or not (any((self.bc, self.release))):
            image += "-SNAPSHOT"
        return image

    def docker_service_name(self):
        return self.name()

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

    def version_lower_than(self, target):
        return parse_version(self.version) < parse_version(target)

    @classmethod
    def name(cls):
        return _camel_hyphen(cls.__name__).lower()

    @classmethod
    def option_name(cls):
        return cls.name().replace("-", "_")

    @property
    def oss(self):
        return self._oss

    @property
    def ubi8(self):
        return self._ubi8

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
        if self._env_vars:
            if isinstance(content["environment"], collections.abc.Mapping):
                for ev in self._env_vars:
                    k, v = ev.split("=", 1)
                    content["environment"][k] = v
            else:
                # it's a list of strings
                content["environment"].extend(self._env_vars)
        return {self.docker_service_name(): content}

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
        parser.add_argument(
            '--' + cls.name() + '-env-var',
            action="append",
            dest=cls.option_name() + "_env_vars",
            help="arbitrary environment variables to set"
        )

    def image_download_url(self):
        pass

    def default_elasticsearch_hosts(self, tls=False):
        if tls:
            return self.DEFAULT_ELASTICSEARCH_HOSTS_TLS
        else:
            return self.DEFAULT_ELASTICSEARCH_HOSTS_NO_TLS

    def default_kibana_hosts(self, tls=False):
        if tls:
            return self.DEFAULT_KIBANA_HOST_TLS
        else:
            return self.DEFAULT_KIBANA_HOST_NO_TLS

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
        if self.ubi8:
            image += "-ubi8"
        key = "{image}-{version}-docker-image.tar.gz".format(
            image=image,
            version=version,
        )
        try:
            print(
                '''WARNING: BCs for Elasticsearch require some manual steps as long as it is not using the same docker repo tags.
                See https://github.com/elastic/apm-integration-testing/issues/1566
                '''
            )
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
        for image_detail_key in ("oss", "release", "snapshot", "ubi8"):
            parser.add_argument(
                "--" + cls.name() + "-" + image_detail_key,
                action="store_true",
                dest=cls.option_name() + "_" + image_detail_key,
                help="stack {} override".format(image_detail_key),
            )
