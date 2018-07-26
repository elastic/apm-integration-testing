#!/usr/bin/env python
"""
CLI for starting a testing environment using docker-compose.
"""
from __future__ import print_function

from abc import abstractmethod

try:
    from urllib.request import urlopen, urlretrieve, Request
except ImportError:
    from urllib import urlretrieve
    from urllib2 import urlopen, Request
import argparse
import collections
import datetime
import functools
import glob
import inspect
import io
import json
import logging
import multiprocessing
import os
import re
import sys
import subprocess
import unittest
try:
    import unittest.mock as mock
except ImportError:
    try:
        import mock
    except ImportError:
        class IgnoreMock(object):
            @staticmethod
            def patch(_):
                return lambda *args: None
        mock = IgnoreMock()

# TODO: convert yaml fixtures and remove this, only needed for tests
try:
    import yaml
except ImportError:
    pass

if sys.version_info[0] == 3:
    stringIO = io.StringIO
else:
    stringIO = io.BytesIO

#
# package info
#
PACKAGE_NAME = 'localmanager'
__version__ = "4.0.0"

DEFAULT_STACK_VERSION = "6.3.3"


#
# helpers
#
def _camel_hyphen(string):
    return re.sub(r'([a-z])([A-Z])', r'\1-\2', string)


def discover_services(mod=None):
    """discover list of services"""
    ret = []
    if not mod:
        mod = sys.modules[__name__]
    for obj in dir(mod):
        cls = getattr(mod, obj)
        if inspect.isclass(cls) and issubclass(cls, Service) \
                and cls not in (Service, OpbeansService):
            ret.append(cls)
    return ret


def _load_image(cache_dir, url):
    filename = os.path.basename(url)
    filepath = os.path.join(cache_dir, filename)
    etag_cache_file = filepath + '.etag'
    if os.path.exists(etag_cache_file):
        with open(etag_cache_file, mode='r') as f:
            etag = f.read().strip()
    else:
        etag = None
    request = Request(url)
    request.get_method = lambda: 'HEAD'
    try:
        response = urlopen(request)
    except Exception as e:
        print('Error while fetching %s: %s' % (url, str(e)))
        return False
    new_etag = response.info().get('ETag')
    if etag == new_etag:
        print("Skipping download of %s, local file is current" % filename)
        return True
    print("downloading", url)
    try:
        os.makedirs(cache_dir)
    except Exception:  # noqa: E722
        pass  # ignore
    try:
        urlretrieve(url, filepath)
    except Exception as e:
        print('Error while fetching %s: %s' % (url, str(e)))
        return False
    subprocess.check_call(["docker", "load", "-i", filepath])
    with open(etag_cache_file, mode='w') as f:
        f.write(new_etag)
    return True


def load_images(urls, cache_dir):
    load_image_fn = functools.partial(_load_image, cache_dir)
    pool = multiprocessing.Pool(4)
    # b/c python2
    try:
        results = pool.map_async(load_image_fn, urls).get(timeout=10000000)
    except KeyboardInterrupt:
        pool.terminate()
        raise
    if not all(results):
        print("Errors while downloading. Exiting.")
        sys.exit(1)


DEFAULT_HEALTHCHECK_INTERVAL = "5s"
DEFAULT_HEALTHCHECK_RETRIES = 12


def curl_healthcheck(port, host="localhost", path="/healthcheck",
                     interval=DEFAULT_HEALTHCHECK_INTERVAL, retries=DEFAULT_HEALTHCHECK_RETRIES):
    return {
                "interval": interval,
                "retries": retries,
                "test": ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null",
                         "http://{}:{}{}".format(host, port, path)]
            }


def parse_version(version):
    res = []
    for x in version.split('.'):
        try:
            y = int(x)
        except ValueError:
            y = int(x.split("-", 1)[0])
        res.append(y)
    return res


class Service(object):
    """encapsulate docker-compose service definition"""

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

        self._bc = options.get(self.option_name() + "_bc") or options.get("bc")
        self._oss = options.get(self.option_name() + "_oss") or options.get("oss")
        self._release = options.get(self.option_name() + "_release") or options.get("release")
        self._snapshot = options.get(self.option_name() + "_snapshot") or options.get("snapshot")

        # version is service specific or stack or default
        self._version = options.get(self.option_name() + "_version") or options.get("version", DEFAULT_STACK_VERSION)

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
        return ["co.elatic.apm.stack-version=" + self.version]

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
    def publish_port(external, internal, expose=False):
        addr = "" if expose else "127.0.0.1:"
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

    def image_download_url(self):
        pass

    @abstractmethod
    def _content(self):
        pass


class DockerLoadableService(object):
    """Mix in for Elastic services that have public docker images built but not available in a registry [yet]"""

    def image_download_url(self):
        # Elastic releases are public
        if self.release:
            return

        version = self.version
        image = self.docker_name
        if self.oss:
            image += "-oss"
        if self.bc:
            return "https://staging.elastic.co/{version}-{sha}/docker/{image}-{version}.tar.gz".format(
                sha=self.bc,
                image=image,
                version=version,
            )

        return "https://snapshots.elastic.co/docker/{image}-{version}-SNAPSHOT.tar.gz".format(
            image=image,
            version=version,
        )


#
# Elastic Services
#
class ApmServer(DockerLoadableService, Service):
    docker_path = "apm"

    SERVICE_PORT = 8200
    DEFAULT_MONITOR_PORT = "6060"
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "kafka", "logstash"}

    def __init__(self, **options):
        super(ApmServer, self).__init__(**options)

        self.apm_server_command_args = [
            ("apm-server.frontend.enabled", "true"),
            ("apm-server.frontend.rate_limit", "100000"),
            ("apm-server.host", "0.0.0.0:8200"),
            ("apm-server.read_timeout", "1m"),
            ("apm-server.shutdown_timeout", "2m"),
            ("apm-server.write_timeout", "1m"),
            ("logging.json", "true"),
            ("logging.metrics.enabled", "false"),
            ("setup.kibana.host", "kibana:5601"),
            ("setup.template.settings.index.number_of_replicas", "0"),
            ("setup.template.settings.index.number_of_shards", "1"),
            ("setup.template.settings.index.refresh_interval", "1ms"),
            ("xpack.monitoring.elasticsearch", "true"),
        ]

        self.apm_server_monitor_port = options.get("apm_server_monitor_port", self.DEFAULT_MONITOR_PORT)
        self.apm_server_output = options.get("apm_server_output", self.DEFAULT_OUTPUT)
        if self.apm_server_output == "elasticsearch":
            self.apm_server_command_args.extend([
                ("output.elasticsearch.enabled", "true"),
                ("output.elasticsearch.hosts", "[elasticsearch:9200]"),
            ])
        else:
            self.apm_server_command_args.extend([
                ("output.elasticsearch.enabled", "false"),
                ("output.elasticsearch.hosts", "[elasticsearch:9200]"),
                ("xpack.monitoring.elasticsearch.hosts", "[\"elasticsearch:9200\"]"),
            ])
            if self.apm_server_output == "kafka":
                self.apm_server_command_args.extend([
                    ("output.kafka.enabled", "true"),
                    ("output.kafka.hosts", "[\"kafka:9092\"]"),
                    ("output.kafka.topics", "[{default: 'apm', topic: 'apm-%{[context.service.name]}'}]"),
                ])
            elif self.apm_server_output == "logstash":
                self.apm_server_command_args.extend([
                    ("output.logstash.enabled", "true"),
                    ("output.logstash.hosts", "[\"logstash:5044\"]"),
                ])

    @classmethod
    def add_arguments(cls, parser):
        super(ApmServer, cls).add_arguments(parser)
        parser.add_argument(
            '--apm-server-output',
            choices=cls.OUTPUTS,
            default='elasticsearch',
            help='apm-server output'
        )

    def _content(self):
        command_args = []
        for param, value in self.apm_server_command_args:
            command_args.extend(["-E", param + "=" + value])
        return dict(
            cap_add=["CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"],
            cap_drop=["ALL"],
            command=["apm-server", "-e"] + command_args,
            depends_on={"elasticsearch": {"condition": "service_healthy"}},
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "apm-server"),
            labels=["co.elatic.apm.stack-version=" + self.version],
            ports=[
                self.publish_port(self.port, self.SERVICE_PORT),
                self.publish_port(self.apm_server_monitor_port, self.DEFAULT_MONITOR_PORT),
            ]
        )

    @staticmethod
    def enabled():
        return True


class Elasticsearch(DockerLoadableService, Service):
    default_environment = ["cluster.name=docker-cluster", "bootstrap.memory_lock=true", "discovery.type=single-node"]
    default_es_java_opts = {
        "-Xms": "1g",
        "-Xmx": "1g",
    }

    SERVICE_PORT = 9200

    def __init__(self, **options):
        super(Elasticsearch, self).__init__(**options)
        if not self.oss and not self.at_least_version("6.3"):
            self.docker_name = self.name() + "-platinum"

        # construct elasticsearch environment variables
        # TODO: add command line option for java options (gr)
        es_java_opts = dict(self.default_es_java_opts)
        if self.at_least_version("6.4"):
            # per https://github.com/elastic/elasticsearch/pull/32138/files
            es_java_opts["-XX:UseAVX"] = "=2"

        java_opts_env = "ES_JAVA_OPTS=" + " ".join(["{}{}".format(k, v) for k, v in es_java_opts.items()])
        self.environment = self.default_environment + [
                java_opts_env, "path.data=/usr/share/elasticsearch/data/" + self.version]
        if not self.oss:
            self.environment.append("xpack.security.enabled=false")
            self.environment.append("xpack.license.self_generated.type=trial")
            if self.at_least_version("6.3"):
                self.environment.append("xpack.monitoring.collection.enabled=true")

    def _content(self):
        return dict(
            environment=self.environment,
            healthcheck={
                "interval": "20",
                "retries": 10,
                "test": ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -vq '\"status\":\"red\"'"],
            },
            mem_limit="5g",
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
            ulimits={
                "memlock": {"hard": -1, "soft": -1},
            },
            volumes=["esdata:/usr/share/elasticsearch/data"]
        )

    @staticmethod
    def enabled():
        return True


class Filebeat(DockerLoadableService, Service):
    docker_path = "beats"

    def __init__(self, **options):
        super(Filebeat, self).__init__(**options)
        config = "filebeat.yml" if self.at_least_version("6.1") else "filebeat.simple.yml"
        self.filebeat_config_path = os.path.join(".", "docker", "filebeat", config)

    def _content(self):
        return dict(
            command="filebeat -e --strict.perms=false",
            depends_on={
                "elasticsearch": {"condition": "service_healthy"},
                "kibana": {"condition": "service_healthy"},
            },
            labels=None,
            user="root",
            volumes=[
                self.filebeat_config_path + ":/usr/share/filebeat/filebeat.yml",
                "/var/lib/docker/containers:/var/lib/docker/containers",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )


class Kibana(DockerLoadableService, Service):
    default_environment = {"SERVER_NAME": "kibana.example.org", "ELASTICSEARCH_URL": "http://elasticsearch:9200"}

    SERVICE_PORT = 5601

    def __init__(self, **options):
        super(Kibana, self).__init__(**options)
        if not self.at_least_version("6.3") and not self.oss:
            self.docker_name = self.name() + "-x-pack"
        self.environment = self.default_environment.copy()
        if not self.oss:
            self.environment["XPACK_MONITORING_ENABLED"] = "true"
            if self.at_least_version("6.3"):
                self.environment["XPACK_XPACK_MAIN_TELEMETRY_ENABLED"] = "false"

    def _content(self):
        return dict(
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "kibana", path="/", interval="5s", retries=20),
            depends_on={"elasticsearch": {"condition": "service_healthy"}},
            environment=self.environment,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )

    @staticmethod
    def enabled():
        return True


class Logstash(DockerLoadableService, Service):
    SERVICE_PORT = 5044

    def _content(self):
        return dict(
            depends_on={"elasticsearch": {"condition": "service_healthy"}},
            environment={"ELASTICSEARCH_URL": "http://elasticsearch:9200"},
            healthcheck=curl_healthcheck(9600, "logstash", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT), "9600"],
            volumes=["./docker/logstash/pipeline/:/usr/share/logstash/pipeline/"]
        )


class Metricbeat(DockerLoadableService, Service):
    docker_path = "beats"

    def _content(self):
        return dict(
            command="metricbeat -e --strict.perms=false",
            depends_on={
                "elasticsearch": {"condition": "service_healthy"},
                "kibana": {"condition": "service_healthy"},
            },
            labels=None,
            user="root",
            volumes=[
                "./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )


#
# Supporting Services
#
class Kafka(Service):
    SERVICE_PORT = 9092

    def _content(self):
        return dict(
            depends_on=["zookeeper"],
            environment={
                "KAFKA_ADVERTISED_LISTENERS": "PLAINTEXT://kafka:9092",
                "KAFKA_BROKER_ID": 1,
                "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR": 1,
                "KAFKA_ZOOKEEPER_CONNECT": "zookeeper:2181",
            },
            image="confluentinc/cp-kafka:4.1.0",
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class Postgres(Service):
    SERVICE_PORT = 5432

    def _content(self):
        return dict(
            environment=["POSTGRES_DB=opbeans", "POSTGRES_PASSWORD=verysecure"],
            healthcheck={"interval": "10s", "test": ["CMD", "pg_isready", "-h", "postgres", "-U", "postgres"]},
            image="postgres:10",
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT, expose=True)],
            volumes=["./docker/opbeans/sql:/docker-entrypoint-initdb.d", "pgdata:/var/lib/postgresql/data"],

        )


class Redis(Service):
    SERVICE_PORT = 6379

    def _content(self):
        return dict(
            healthcheck={"interval": "10s", "test": ["CMD", "redis-cli", "ping"]},
            image="redis:4",
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT, expose=True)],
        )


class Zookeeper(Service):
    SERVICE_PORT = 2181

    def _content(self):
        return dict(
            environment={
                "ZOOKEEPER_CLIENT_PORT": 2181,
                "ZOOKEEPER_TICK_TIME": 2000,
            },
            image="confluentinc/cp-zookeeper:latest",
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


#
# Agent Integration Test Services
#
class AgentGoNetHttp(Service):
    SERVICE_PORT = 8080

    def _content(self):
        return dict(
            build={"context": "docker/go/nethttp", "dockerfile": "Dockerfile"},
            container_name="gonethttpapp",
            image=None,
            labels=None,
            logging=None,
            environment={
                "ELASTIC_APM_SERVICE_NAME": "gonethttpapp",
                "ELASTIC_APM_SERVER_URL": "http://apm-server:8200",
                "ELASTIC_APM_TRANSACTION_IGNORE_NAMES": "healthcheck",
                "ELASTIC_APM_FLUSH_INTERVAL": "500ms",
            },
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentNodejsExpress(Service):
    # elastic/apm-agent-nodejs#master
    DEFAULT_AGENT_PACKAGE = "elastic-apm-node"
    SERVICE_PORT = 8010

    def __init__(self, **options):
        super(AgentNodejsExpress, self).__init__(**options)
        self.agent_package = options.get("nodejs_agent_package", self.DEFAULT_AGENT_PACKAGE)

    @classmethod
    def add_arguments(cls, parser):
        super(AgentNodejsExpress, cls).add_arguments(parser)
        parser.add_argument(
            '--nodejs-agent-package',
            default=cls.DEFAULT_AGENT_PACKAGE,
        )

    def _content(self):
        return dict(
            build={"context": "docker/nodejs/express", "dockerfile": "Dockerfile"},
            command="bash -c \"npm install {} && node app.js\"".format(
                self.agent_package, self.SERVICE_PORT),
            container_name="expressapp",
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "expressapp"),
            image=None,
            labels=None,
            logging=None,
            environment={
                "APM_SERVER_URL": "http://apm-server:8200",
                "EXPRESS_PORT": str(self.SERVICE_PORT),
                "EXPRESS_SERVICE_NAME": "expressapp",
            },
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentPython(Service):
    DEFAULT_AGENT_PACKAGE = "elastic-apm"
    _arguments_added = False

    def __init__(self, **options):
        super(AgentPython, self).__init__(**options)
        self.agent_package = options.get("python_agent_package", self.DEFAULT_AGENT_PACKAGE)

    @classmethod
    def add_arguments(cls, parser):
        if cls._arguments_added:
            return

        super(AgentPython, cls).add_arguments(parser)
        parser.add_argument(
            '--python-agent-package',
            default=cls.DEFAULT_AGENT_PACKAGE,
        )
        # prevent calling again
        cls._arguments_added = True

    def _content(self):
        raise NotImplemented


class AgentPythonDjango(AgentPython):
    SERVICE_PORT = 8003

    def _content(self):
        return dict(
            build={"context": "docker/python/django", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -U {} && python testapp/manage.py runserver 0.0.0.0:{}\"".format(
                self.agent_package, self.SERVICE_PORT),
            container_name="djangoapp",
            environment={
                "APM_SERVER_URL": "http://apm-server:8200",
                "DJANGO_PORT": self.SERVICE_PORT,
                "DJANGO_SERVICE_NAME": "djangoapp",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "djangoapp"),
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentPythonFlask(AgentPython):
    SERVICE_PORT = 8001

    def _content(self):
        return dict(
            build={"context": "docker/python/flask", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -U {} && gunicorn app:app\"".format(self.agent_package),
            container_name="flaskapp",
            image=None,
            labels=None,
            logging=None,
            environment={
                "APM_SERVER_URL": "http://apm-server:8200",
                "FLASK_SERVICE_NAME": "flaskapp",
                "GUNICORN_CMD_ARGS": "-w 4 -b 0.0.0.0:{}".format(self.SERVICE_PORT),
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "flaskapp"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentRubyRails(Service):
    DEFAULT_AGENT_VERSION = "latest"
    DEFAULT_AGENT_VERSION_STATE = "release"
    SERVICE_PORT = 8020

    @classmethod
    def add_arguments(cls, parser):
        super(AgentRubyRails, cls).add_arguments(parser)
        parser.add_argument(
            "--ruby-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
        )
        parser.add_argument(
            "--ruby-agent-version-state",
            default=cls.DEFAULT_AGENT_VERSION_STATE,
        )

    def __init__(self, **options):
        super(AgentRubyRails, self).__init__(**options)
        self.agent_version = options.get("ruby_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_version_state = options.get("ruby_agent_version_state", self.DEFAULT_AGENT_VERSION_STATE)

    def _content(self):
        return dict(
            build={"context": "docker/ruby/rails", "dockerfile": "Dockerfile"},
            command="bash -c \"bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p {}\"".format(
                self.SERVICE_PORT),
            container_name="railsapp",
            environment={
                "APM_SERVER_URL": "http://apm-server:8200",
                "ELASTIC_APM_SERVER_URL": "http://apm-server:8200",
                "ELASTIC_APM_SERVICE_NAME": "railsapp",
                "RAILS_PORT": self.SERVICE_PORT,
                "RAILS_SERVICE_NAME": "railsapp",
                "RUBY_AGENT_VERSION_STATE": self.agent_version_state,
                "RUBY_AGENT_VERSION": self.agent_version,
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "railsapp", interval="10s", retries=60),
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentJavaSpring(Service):
    SERVICE_PORT = 8090

    def _content(self):
        return dict(
            build={"context": "docker/java/spring", "dockerfile": "Dockerfile"},
            container_name="javaspring",
            image=None,
            labels=None,
            logging=None,
            environment={
                "ELASTIC_APM_SERVICE_NAME": "springapp",
                "ELASTIC_APM_SERVER_URL": "http://apm-server:8200",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "javaspring"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )

#
# Opbeans Services
#


class OpbeansService(Service):
    DEFAULT_APM_SERVER_URL = "http://apm-server:8200"

    def __init__(self, **options):
        super(OpbeansService, self).__init__(**options)
        self.apm_server_url = options.get("opbeans_apm_server_url", self.DEFAULT_APM_SERVER_URL)

    @classmethod
    def add_arguments(cls, parser):
        """add service-specific command line arguments"""
        # allow port overrides
        super(OpbeansService, cls).add_arguments(parser)
        if hasattr(cls, 'DEFAULT_SERVICE_NAME'):
            parser.add_argument(
                '--' + cls.name() + '-service-name',
                default=cls.DEFAULT_SERVICE_NAME,
                dest=cls.option_name() + '_service_name',
                help="service name"
            )


class OpbeansGo(OpbeansService):
    SERVICE_PORT = 3003
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-go"

    def __init__(self, **options):
        super(OpbeansGo, self).__init__(**options)
        self.agent_branch = options.get("opbeans_agent_branch", self.DEFAULT_AGENT_BRANCH)
        self.agent_repo = options.get("opbeans_agent_repo", self.DEFAULT_AGENT_REPO)

    def _content(self):
        depends_on = {
            "elasticsearch": {"condition": "service_healthy"},
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if not self.options.get("disable_apm_server", False):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/go",
                dockerfile="Dockerfile",
                args=[
                    "GO_AGENT_BRANCH=" + self.agent_branch,
                    "GO_AGENT_REPO=" + self.agent_repo,
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL=http://localhost:8200",
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_SAMPLE_RATE=1",
                "ELASTICSEARCH_URL=http://elasticsearch:9200",
                "OPBEANS_CACHE=redis://redis:6379",
                "OPBEANS_PORT={:d}".format(self.SERVICE_PORT),
                "PGHOST=postgres",
                "PGPORT=5432",
                "PGUSER=postgres",
                "PGPASSWORD=verysecure",
                "PGSSLMODE=disable",
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
        return content


class OpbeansJava(OpbeansService):
    SERVICE_PORT = 3002
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-java"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = 'opbeans-java'

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansJava, cls).add_arguments(parser)
        parser.add_argument(
            '--opbeans-java-local-repo',
            default=cls.DEFAULT_LOCAL_REPO,
        )

    def __init__(self, **options):
        super(OpbeansJava, self).__init__(**options)
        self.local_repo = options.get("opbeans_java_local_repo", self.DEFAULT_LOCAL_REPO)
        self.agent_branch = options.get("opbeans_agent_branch", self.DEFAULT_AGENT_BRANCH)
        self.agent_repo = options.get("opbeans_agent_repo", self.DEFAULT_AGENT_REPO)
        self.service_name = options.get("opbeans_java_service_name", self.DEFAULT_SERVICE_NAME)

    def _content(self):
        depends_on = {
            "elasticsearch": {"condition": "service_healthy"},
            "postgres": {"condition": "service_healthy"},
        }

        if not self.options.get("disable_apm_server", False):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/java",
                dockerfile="Dockerfile",
                args=[
                    "JAVA_AGENT_BRANCH=" + self.agent_branch,
                    "JAVA_AGENT_REPO=" + self.agent_repo,
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_APPLICATION_PACKAGES=co.elastic.apm.opbeans",
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_SAMPLE_RATE=1",
                "DATABASE_URL=jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure",
                "DATABASE_DIALECT=POSTGRESQL",
                "DATABASE_DRIVER=org.postgresql.Driver",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL=http://elasticsearch:9200",
                "OPBEANS_SERVER_PORT={:d}".format(self.SERVICE_PORT),
                "JAVA_AGENT_VERSION",
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "opbeans-java", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
            volumes=[
                "{}:/local-install".format(self.local_repo),
            ]
        )
        return content


class OpbeansNode(OpbeansService):
    SERVICE_PORT = 3000
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = "opbeans-node"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansNode, cls).add_arguments(parser)
        parser.add_argument(
            '--opbeans-node-local-repo',
            default=cls.DEFAULT_LOCAL_REPO,
        )

    def __init__(self, **options):
        super(OpbeansNode, self).__init__(**options)
        self.local_repo = options.get("opbeans_node_local_repo", self.DEFAULT_LOCAL_REPO)
        self.service_name = options.get("opbeans_node_service_name", self.DEFAULT_SERVICE_NAME)

    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if not self.options.get("disable_apm_server", False):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build={"context": "docker/opbeans/node", "dockerfile": "Dockerfile"},
            environment=[
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_APP_NAME=opbeans-node",
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_LOG_LEVEL=debug",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "WORKLOAD_ELASTIC_APM_APP_NAME=workload",
                "WORKLOAD_ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "OPBEANS_SERVER_PORT=3000",
                "OPBEANS_SERVER_HOSTNAME=opbeans-node",
                "NODE_ENV=production",
                "PGHOST=postgres",
                "PGPASSWORD=verysecure",
                "PGPORT=5432",
                "PGUSER=postgres",
                "REDIS_URL=redis://redis:6379",
                "NODE_AGENT_BRANCH=1.x",
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(3000, "opbeans-node", path="/"),
            ports=[self.publish_port(self.port, 3000)],
            volumes=[
                "{}:/local-install".format(self.local_repo),
                "./docker/opbeans/node/sourcemaps:/sourcemaps",
            ]
        )
        return content


class OpbeansPython(OpbeansService):
    SERVICE_PORT = 8000
    DEFAULT_AGENT_REPO = "elastic/apm-agent-python"
    DEFAULT_AGENT_BRANCH = "2.x"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = 'opbeans-python'

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansPython, cls).add_arguments(parser)
        parser.add_argument(
            '--opbeans-python-local-repo',
            default=cls.DEFAULT_LOCAL_REPO,
        )

    def __init__(self, **options):
        super(OpbeansPython, self).__init__(**options)
        self.local_repo = options.get("opbeans_python_local_repo", self.DEFAULT_LOCAL_REPO)
        if self.version.split(".", 3)[0:2] < ["6", "2"]:
            self.agent_branch = "1.x"
        else:
            self.agent_branch = self.DEFAULT_AGENT_BRANCH
        self.agent_repo = options.get("opbeans_agent_repo", self.DEFAULT_AGENT_REPO)
        self.service_name = options.get("opbeans_python_service_name", self.DEFAULT_SERVICE_NAME)

    def _content(self):
        depends_on = {
            "elasticsearch": {"condition": "service_healthy"},
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if not self.options.get("disable_apm_server", False):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build={"context": "docker/opbeans/python", "dockerfile": "Dockerfile"},
            environment=[
                "DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans",
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL=http://elasticsearch:9200",
                "OPBEANS_SERVER_URL=http://opbeans-python:3000",
                "PYTHON_AGENT_BRANCH=" + self.agent_branch,
                "PYTHON_AGENT_REPO=" + self.agent_repo,
                "PYTHON_AGENT_VERSION",
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(3000, "opbeans-python", path="/"),
            ports=[self.publish_port(self.port, 3000)],
            volumes=[
                "{}:/local-install".format(self.local_repo),
            ]
        )
        return content


class OpbeansRuby(OpbeansService):
    SERVICE_PORT = 3001
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-ruby"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = "opbeans-ruby"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansRuby, cls).add_arguments(parser)
        parser.add_argument(
            '--opbeans-ruby-local-repo',
            default=cls.DEFAULT_LOCAL_REPO,
        )

    def __init__(self, **options):
        super(OpbeansRuby, self).__init__(**options)
        self.local_repo = options.get("opbeans_ruby_local_repo", self.DEFAULT_LOCAL_REPO)
        self.agent_branch = options.get("opbeans_agent_branch", self.DEFAULT_AGENT_BRANCH)
        self.agent_repo = options.get("opbeans_agent_repo", self.DEFAULT_AGENT_REPO)
        self.service_name = options.get("opbeans_ruby_service_name", self.DEFAULT_SERVICE_NAME)

    def _content(self):
        depends_on = {
            "elasticsearch": {"condition": "service_healthy"},
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if not self.options.get("disable_apm_server", False):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build={"context": "docker/opbeans/ruby", "dockerfile": "Dockerfile"},
            environment=[
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL=http://elasticsearch:9200",
                "OPBEANS_SERVER_URL=http://opbeans-ruby:{:d}".format(self.SERVICE_PORT),
                "RAILS_ENV=production",
                "RAILS_LOG_TO_STDOUT=1",
                "PORT={:d}".format(self.SERVICE_PORT),
                "RUBY_AGENT_BRANCH=" + self.agent_branch,
                "RUBY_AGENT_REPO=" + self.agent_repo,
                "RUBY_AGENT_VERSION",
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "opbeans-ruby", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
            volumes=[
                "{}:/local-install".format(self.local_repo),
            ]
        )
        return content


class OpbeansRum(Service):
    # OpbeansRum is not really an Opbeans service, so we inherit from Service
    SERVICE_PORT = 9222

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansRum, cls).add_arguments(parser)
        parser.add_argument(
            '--opbeans-rum-backend-service',
            default='opbeans-node',
        )
        parser.add_argument(
            '--opbeans-rum-backend-port',
            default='3000',
        )

    def __init__(self, **options):
        super(OpbeansRum, self).__init__(**options)
        self.backend_service = options.get('opbeans_rum_backend_service', 'opbeans-node')
        self.backend_port = options.get('opbeans_rum_backend_port', '3000')

    def _content(self):
        content = dict(
            build={"context": "docker/opbeans/rum", "dockerfile": "Dockerfile"},
            cap_add=["SYS_ADMIN"],
            depends_on={self.backend_service: {'condition': 'service_healthy'}},
            environment=[
                "OPBEANS_BASE_URL=http://{}:{}".format(self.backend_service, self.backend_port),
            ],
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "opbeans-rum", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
        return content


#
# Service Tests
#
class ServiceTest(unittest.TestCase):
    maxDiff = None


class AgentServiceTest(ServiceTest):
    def test_agent_go_net_http(self):
        agent = AgentGoNetHttp().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-go-net-http:
                    build:
                        dockerfile: Dockerfile
                        context: docker/go/nethttp
                    container_name: gonethttpapp
                    environment:
                        ELASTIC_APM_SERVICE_NAME: gonethttpapp
                        ELASTIC_APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_TRANSACTION_IGNORE_NAMES: healthcheck
                        ELASTIC_APM_FLUSH_INTERVAL: 500ms
                    ports:
                        - 127.0.0.1:8080:8080
            """)
        )

    def test_agent_nodejs_express(self):
        agent = AgentNodejsExpress().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-nodejs-express:
                    build:
                        dockerfile: Dockerfile
                        context: docker/nodejs/express
                    container_name: expressapp
                    command: bash -c "npm install elastic-apm-node && node app.js"
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        EXPRESS_SERVICE_NAME: expressapp
                        EXPRESS_PORT: "8010"
                    healthcheck:
                        interval: 5s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://expressapp:8010/healthcheck"]
                    ports:
                        - 127.0.0.1:8010:8010
            """)  # noqa: 501
        )

        vagent = AgentNodejsExpress(nodejs_agent_package="elastic/apm-agent-nodejs#test").render()
        self.assertEqual('bash -c "npm install elastic/apm-agent-nodejs#test && node app.js"',
                         vagent["agent-nodejs-express"]["command"])

    def test_agent_python_django(self):
        agent = AgentPythonDjango().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-python-django:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/django
                    command: bash -c "pip install -U elastic-apm && python testapp/manage.py runserver 0.0.0.0:8003"
                    container_name: djangoapp
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        DJANGO_SERVICE_NAME: djangoapp
                        DJANGO_PORT: 8003
                    healthcheck:
                        interval: 5s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://djangoapp:8003/healthcheck"]
                    ports:
                        - 127.0.0.1:8003:8003
            """)  # noqa: 501
        )

    def test_agent_python_flask(self):
        agent = AgentPythonFlask(version="6.2.4").render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-python-flask:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/flask
                    command: bash -c "pip install -U elastic-apm && gunicorn app:app"
                    container_name: flaskapp
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        FLASK_SERVICE_NAME: flaskapp
                        GUNICORN_CMD_ARGS: "-w 4 -b 0.0.0.0:8001"
                    healthcheck:
                        interval: 5s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://flaskapp:8001/healthcheck"]
                    ports:
                        - 127.0.0.1:8001:8001
            """)  # noqa: 501
        )

    def test_agent_ruby_rails(self):
        agent = AgentRubyRails().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-ruby-rails:
                    build:
                        dockerfile: Dockerfile
                        context: docker/ruby/rails
                    container_name: railsapp
                    command: bash -c "bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p 8020"
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_SERVICE_NAME: railsapp
                        RAILS_SERVICE_NAME: railsapp
                        RAILS_PORT: 8020
                        RUBY_AGENT_VERSION: latest
                        RUBY_AGENT_VERSION_STATE: release
                    healthcheck:
                        interval: 10s
                        retries: 60
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://railsapp:8020/healthcheck"]
                    ports:
                        - 127.0.0.1:8020:8020
            """)  # noqa: 501
        )

    def test_agent_java_spring(self):
        agent = AgentJavaSpring().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-java-spring:
                    build:
                        dockerfile: Dockerfile
                        context: docker/java/spring
                    container_name: javaspring
                    environment:
                        ELASTIC_APM_SERVICE_NAME: springapp
                        ELASTIC_APM_SERVER_URL: http://apm-server:8200
                    healthcheck:
                        interval: 5s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output",
                        "/dev/null", "http://javaspring:8090/healthcheck"]
                    ports:
                        - 127.0.0.1:8090:8090
            """)
        )


class ApmServerServiceTest(ServiceTest):
    def test_default_buildcandidate(self):
        apm_server = ApmServer(version="6.3.100", bc=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server:6.3.100"
        )

    def test_default_snapshot(self):
        apm_server = ApmServer(version="6.3.100", snapshot=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server:6.3.100-SNAPSHOT"
        )

    def test_default_release(self):
        apm_server = ApmServer(version="6.3.100", release=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server:6.3.100"
        )

    def test_oss_buildcandidate(self):
        apm_server = ApmServer(version="6.3.100", oss=True, bc="123").render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server-oss:6.3.100"
        )

    def test_oss_snapshot(self):
        apm_server = ApmServer(version="6.3.100", oss=True, snapshot=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server-oss:6.3.100-SNAPSHOT"
        )

    def test_oss_release(self):
        apm_server = ApmServer(version="6.3.100", oss=True, release=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server-oss:6.3.100"
        )

    def test_elasticsearch_output(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="elasticsearch").render()["apm-server"]
        self.assertFalse(
            any(e.startswith("xpack.monitoring.elasticsearch.hosts=") for e in apm_server["command"]),
            "xpack.monitoring.elasticsearch.hosts while output=elasticsearch"
        )
        self.assertTrue(
            any(e == "output.elasticsearch.enabled=true" for e in apm_server["command"]),
            "output.elasticsearch.enabled not true while output=elasticsearch"
        )

    def test_logstash_output(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="logstash").render()["apm-server"]
        self.assertTrue(
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]" in apm_server["command"],
            "xpack.monitoring.elasticsearch.hosts not set while output=logstash"
        )
        self.assertTrue(
            any(e == "output.elasticsearch.enabled=false" for e in apm_server["command"]),
            "output.elasticsearch.enabled not false while output=elasticsearch"
        )
        logstash_options = [
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
        ]
        for o in logstash_options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=logstash".format(o))

    def test_kafka_output(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="kafka").render()["apm-server"]
        self.assertTrue(
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]" in apm_server["command"],
            "xpack.monitoring.elasticsearch.hosts not set while output=kafka"
        )
        self.assertTrue(
            any(e == "output.elasticsearch.enabled=false" for e in apm_server["command"]),
            "output.elasticsearch.enabled not false while output=elasticsearch"
        )
        kafka_options = [
            "output.kafka.enabled=true",
            "output.kafka.hosts=[\"kafka:9092\"]",
            "output.kafka.topics=[{default: 'apm', topic: 'apm-%{[context.service.name]}'}]",
        ]
        for o in kafka_options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=kafka".format(o))

    def test_apm_server_custom_port(self):
        custom_port = "8203"
        apm_server = ApmServer(version="6.3.100", apm_server_port=custom_port).render()["apm-server"]
        self.assertTrue(
            "127.0.0.1:{}:8200".format(custom_port) in apm_server["ports"], apm_server["ports"]
        )

    def test_apm_server_custom_version(self):
        apm_server = ApmServer(version="6.3.100", apm_server_version="6.12.0", release=True).render()["apm-server"]
        self.assertEqual(apm_server["image"], "docker.elastic.co/apm/apm-server:6.12.0")
        self.assertEqual(apm_server["image"], "docker.elastic.co/apm/apm-server:6.12.0")
        self.assertEqual(apm_server["labels"], ["co.elatic.apm.stack-version=6.12.0"])


class ElasticsearchServiceTest(ServiceTest):
    def test_6_2_release(self):
        elasticsearch = Elasticsearch(version="6.2.4", release=True).render()["elasticsearch"]
        self.assertEqual(
            elasticsearch["image"], "docker.elastic.co/elasticsearch/elasticsearch-platinum:6.2.4"
        )
        self.assertTrue(
            "xpack.security.enabled=false" in elasticsearch["environment"], "xpack.security.enabled=false"
        )
        self.assertTrue(
            "xpack.license.self_generated.type=trial" in elasticsearch["environment"], "xpack.license type"
        )
        self.assertTrue("127.0.0.1:9200:9200" in elasticsearch["ports"])

    def test_6_2_oss_release(self):
        elasticsearch = Elasticsearch(version="6.2.4", oss=True, release=True).render()["elasticsearch"]
        self.assertEqual(
            elasticsearch["image"], "docker.elastic.co/elasticsearch/elasticsearch-oss:6.2.4"
        )
        self.assertFalse(
            any(e.startswith("xpack.security.enabled=") for e in elasticsearch["environment"]),
            "xpack.security.enabled set while oss"
        )

    def test_6_3_snapshot(self):
        elasticsearch = Elasticsearch(version="6.3.100", snapshot=True).render()["elasticsearch"]
        self.assertEqual(
            elasticsearch["image"], "docker.elastic.co/elasticsearch/elasticsearch:6.3.100-SNAPSHOT"
        )
        self.assertTrue(
            "xpack.security.enabled=false" in elasticsearch["environment"], "xpack.security.enabled=false"
        )
        self.assertTrue(
            "xpack.license.self_generated.type=trial" in elasticsearch["environment"], "xpack.license type"
        )


class FilebeatServiceTest(ServiceTest):
    def test_filebeat_pre_6_1(self):
        filebeat = Filebeat(version="6.0.4", release=True).render()
        self.assertEqual(
            filebeat, yaml.load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.0.4
                    container_name: localtesting_6.0.4_filebeat
                    user: root
                    command: filebeat -e --strict.perms=false
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/filebeat/filebeat.simple.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )

    def test_filebeat_post_6_1(self):
        filebeat = Filebeat(version="6.1.1", release=True).render()
        self.assertEqual(
            filebeat, yaml.load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.1.1
                    container_name: localtesting_6.1.1_filebeat
                    user: root
                    command: filebeat -e --strict.perms=false
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )


class KafkaServiceTest(ServiceTest):
    def test_kafka(self):
        kafka = Kafka(version="6.2.4").render()
        self.assertEqual(
            kafka, yaml.load("""
                kafka:
                    image: confluentinc/cp-kafka:4.1.0
                    container_name: localtesting_6.2.4_kafka
                    depends_on:
                        - zookeeper
                    environment:
                        KAFKA_BROKER_ID: 1
                        KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
                        KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
                        KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
                    ports:
                        - 127.0.0.1:9092:9092
            """)
        )


class KibanaServiceTest(ServiceTest):
    def test_6_2_release(self):
        kibana = Kibana(version="6.2.4", release=True).render()
        self.assertEqual(
            kibana, yaml.load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana-x-pack:6.2.4
                    container_name: localtesting_6.2.4_kibana
                    environment:
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_URL: http://elasticsearch:9200
                        XPACK_MONITORING_ENABLED: 'true'
                    ports:
                        - "127.0.0.1:5601:5601"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://kibana:5601/"]
                        interval: 5s
                        retries: 20
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                    labels:
                        - co.elatic.apm.stack-version=6.2.4""")  # noqa: 501
        )

    def test_6_3_release(self):
        kibana = Kibana(version="6.3.5", release=True).render()
        self.assertDictEqual(
            kibana, yaml.load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana:6.3.5
                    container_name: localtesting_6.3.5_kibana
                    environment:
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_URL: http://elasticsearch:9200
                        XPACK_MONITORING_ENABLED: 'true'
                        XPACK_XPACK_MAIN_TELEMETRY_ENABLED: 'false'
                    ports:
                        - "127.0.0.1:5601:5601"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://kibana:5601/"]
                        interval: 5s
                        retries: 20
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                    labels:
                        - co.elatic.apm.stack-version=6.3.5""")  # noqa: 501
        )


class LogstashServiceTest(ServiceTest):
    def test_snapshot(self):
        logstash = Logstash(version="6.2.4", snapshot=True).render()["logstash"]
        self.assertEqual(
            logstash["image"], "docker.elastic.co/logstash/logstash:6.2.4-SNAPSHOT"
        )
        self.assertTrue(
            "127.0.0.1:5044:5044" in logstash["ports"]
        )

    def test_logstash(self):
        logstash = Logstash(version="6.3.0", release=True).render()
        self.assertEqual(
            logstash, yaml.load("""
        logstash:
            container_name: localtesting_6.3.0_logstash
            depends_on:
                elasticsearch: {condition: service_healthy}
            environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200'}
            healthcheck:
                test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://logstash:9600/"]
                interval: 5s
                retries: 12
            image: docker.elastic.co/logstash/logstash:6.3.0
            labels: [co.elatic.apm.stack-version=6.3.0]
            logging:
                driver: json-file
                options: {max-file: '5', max-size: 2m}
            ports: ['127.0.0.1:5044:5044', '9600']
            volumes: ['./docker/logstash/pipeline/:/usr/share/logstash/pipeline/']""")  # noqa: 501

        )


class MetricbeatServiceTest(ServiceTest):
    def test_metricbeat(self):
        metricbeat = Metricbeat(version="6.2.4", release=True).render()
        self.assertEqual(
            metricbeat, yaml.load("""
                metricbeat:
                    image: docker.elastic.co/beats/metricbeat:6.2.4
                    container_name: localtesting_6.2.4_metricbeat
                    user: root
                    command: metricbeat -e --strict.perms=false
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )


class OpbeansServiceTest(ServiceTest):
    def test_opbeans_go(self):
        opbeans_go = OpbeansGo(version="6.3.10").render()
        self.assertEqual(
            opbeans_go, yaml.load("""
                opbeans-go:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/go
                      args:
                        - GO_AGENT_BRANCH=master
                        - GO_AGENT_REPO=elastic/apm-agent-go
                    container_name: localtesting_6.3.10_opbeans-go
                    ports:
                      - "127.0.0.1:3003:3003"
                    environment:
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_JS_SERVER_URL=http://localhost:8200
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTIC_APM_SAMPLE_RATE=1
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_CACHE=redis://redis:6379
                      - OPBEANS_PORT=3003
                      - PGHOST=postgres
                      - PGPORT=5432
                      - PGUSER=postgres
                      - PGPASSWORD=verysecure
                      - PGSSLMODE=disable
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      elasticsearch:
                        condition: service_healthy
                      postgres:
                        condition: service_healthy
                      redis:
                        condition: service_healthy
                      apm-server:
                        condition: service_healthy""")  # noqa: 501
        )

    def test_opbeans_java(self):
        opbeans_java = OpbeansJava(version="6.3.10").render()
        self.assertEqual(
            opbeans_java, yaml.load("""
                opbeans-java:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/java
                      args:
                        - JAVA_AGENT_BRANCH=master
                        - JAVA_AGENT_REPO=elastic/apm-agent-java
                    container_name: localtesting_6.3.10_opbeans-java
                    ports:
                      - "127.0.0.1:3002:3002"
                    environment:
                      - ELASTIC_APM_SERVICE_NAME=opbeans-java
                      - ELASTIC_APM_APPLICATION_PACKAGES=co.elastic.apm.opbeans
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTIC_APM_SAMPLE_RATE=1
                      - DATABASE_URL=jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure
                      - DATABASE_DIALECT=POSTGRESQL
                      - DATABASE_DRIVER=org.postgresql.Driver
                      - REDIS_URL=redis://redis:6379
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_SERVER_PORT=3002
                      - JAVA_AGENT_VERSION
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      elasticsearch:
                        condition: service_healthy
                      postgres:
                        condition: service_healthy
                      apm-server:
                        condition: service_healthy
                    volumes:
                      - .:/local-install
                    healthcheck:
                      test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-java:3002/"]
                      interval: 5s
                      retries: 12""")  # noqa: 501
        )

    def test_opbeans_node(self):
        opbeans_node = OpbeansNode(version="6.2.4").render()
        self.assertEqual(
            opbeans_node, yaml.load("""
                opbeans-node:
                    build:
                        dockerfile: Dockerfile
                        context: docker/opbeans/node
                    container_name: localtesting_6.2.4_opbeans-node
                    ports:
                        - "127.0.0.1:3000:3000"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    environment:
                        - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                        - ELASTIC_APM_APP_NAME=opbeans-node
                        - ELASTIC_APM_SERVICE_NAME=opbeans-node
                        - ELASTIC_APM_LOG_LEVEL=debug
                        - ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5
                        - ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES
                        - WORKLOAD_ELASTIC_APM_APP_NAME=workload
                        - WORKLOAD_ELASTIC_APM_SERVER_URL=http://apm-server:8200
                        - OPBEANS_SERVER_PORT=3000
                        - OPBEANS_SERVER_HOSTNAME=opbeans-node
                        - NODE_ENV=production
                        - PGHOST=postgres
                        - PGPASSWORD=verysecure
                        - PGPORT=5432
                        - PGUSER=postgres
                        - REDIS_URL=redis://redis:6379
                        - NODE_AGENT_BRANCH=1.x
                    depends_on:
                        redis:
                            condition: service_healthy
                        postgres:
                            condition: service_healthy
                        apm-server:
                            condition: service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-node:3000/"]
                        interval: 5s
                        retries: 12
                    volumes:
                        - .:/local-install
                        - ./docker/opbeans/node/sourcemaps:/sourcemaps""")  # noqa: 501
        )

    def test_opbeans_python(self):
        opbeans_python = OpbeansPython(version="6.2.4").render()
        self.assertEqual(
            opbeans_python, yaml.load("""
                opbeans-python:
                    build:
                        dockerfile: Dockerfile
                        context: docker/opbeans/python
                    container_name: localtesting_6.2.4_opbeans-python
                    ports:
                        - "127.0.0.1:8000:3000"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    environment:
                        - DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans
                        - ELASTIC_APM_SERVICE_NAME=opbeans-python
                        - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                        - ELASTIC_APM_FLUSH_INTERVAL=5
                        - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                        - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.5
                        - ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5
                        - ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES
                        - REDIS_URL=redis://redis:6379
                        - ELASTICSEARCH_URL=http://elasticsearch:9200
                        - OPBEANS_SERVER_URL=http://opbeans-python:3000
                        - PYTHON_AGENT_BRANCH=2.x
                        - PYTHON_AGENT_REPO=elastic/apm-agent-python
                        - PYTHON_AGENT_VERSION
                    depends_on:
                        apm-server:
                            condition: service_healthy
                        elasticsearch:
                            condition: service_healthy
                        postgres:
                            condition: service_healthy
                        redis:
                            condition: service_healthy
                    volumes:
                        - .:/local-install
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-python:3000/"]
                        interval: 5s
                        retries: 12
            """)  # noqa: 501
        )

    def test_opbeans_python_branch(self):
        opbeans_python_6_1 = OpbeansPython(version="6.1").render()["opbeans-python"]
        branch = [e for e in opbeans_python_6_1["environment"] if e.startswith("PYTHON_AGENT_BRANCH")]
        self.assertEqual(branch, ["PYTHON_AGENT_BRANCH=1.x"])

        opbeans_python_master = OpbeansPython(version="7.0.0-alpha1").render()["opbeans-python"]
        branch = [e for e in opbeans_python_master["environment"] if e.startswith("PYTHON_AGENT_BRANCH")]
        self.assertEqual(branch, ["PYTHON_AGENT_BRANCH=2.x"])

    def test_opbeans_python_repo(self):
        agent_repo_default = OpbeansPython().render()["opbeans-python"]
        branch = [e for e in agent_repo_default["environment"] if e.startswith("PYTHON_AGENT_REPO")]
        self.assertEqual(branch, ["PYTHON_AGENT_REPO=elastic/apm-agent-python"])

        agent_repo_override = OpbeansPython(opbeans_agent_repo="myrepo").render()["opbeans-python"]
        branch = [e for e in agent_repo_override["environment"] if e.startswith("PYTHON_AGENT_REPO")]
        self.assertEqual(branch, ["PYTHON_AGENT_REPO=myrepo"])

    def test_opbeans_ruby(self):
        opbeans_ruby = OpbeansRuby(version="6.3.10").render()
        self.assertEqual(
            opbeans_ruby, yaml.load("""
                opbeans-ruby:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/ruby
                    container_name: localtesting_6.3.10_opbeans-ruby
                    ports:
                      - "127.0.0.1:3001:3001"
                    environment:
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_SERVICE_NAME=opbeans-ruby
                      - DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby
                      - REDIS_URL=redis://redis:6379
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_SERVER_URL=http://opbeans-ruby:3001
                      - RAILS_ENV=production
                      - RAILS_LOG_TO_STDOUT=1
                      - PORT=3001
                      - RUBY_AGENT_BRANCH=master
                      - RUBY_AGENT_REPO=elastic/apm-agent-ruby
                      - RUBY_AGENT_VERSION
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      redis:
                        condition: service_healthy
                      elasticsearch:
                        condition: service_healthy
                      postgres:
                        condition: service_healthy
                      apm-server:
                        condition: service_healthy
                    volumes:
                      - .:/local-install
                    healthcheck:
                      test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-ruby:3001/"]
                      interval: 5s
                      retries: 12""")  # noqa: 501

        )

    def test_opbeans_rum(self):
        opbeans_rum = OpbeansRum(version="6.3.10").render()
        self.assertEqual(
            opbeans_rum, yaml.load("""
                opbeans-rum:
                     build:
                         dockerfile: Dockerfile
                         context: docker/opbeans/rum
                     container_name: localtesting_6.3.10_opbeans-rum
                     environment:
                         - OPBEANS_BASE_URL=http://opbeans-node:3000
                     cap_add:
                         - SYS_ADMIN
                     ports:
                         - "127.0.0.1:9222:9222"
                     logging:
                          driver: 'json-file'
                          options:
                              max-size: '2m'
                              max-file: '5'
                     depends_on:
                         opbeans-node:
                             condition: service_healthy
                     healthcheck:
                         test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-rum:9222/"]
                         interval: 5s
                         retries: 12""")  # noqa: 501
        )


class PostgresServiceTest(ServiceTest):
    def test_postgres(self):
        postgres = Postgres(version="6.2.4").render()
        self.assertEqual(
            postgres, yaml.load("""
                postgres:
                    image: postgres:10
                    container_name: localtesting_6.2.4_postgres
                    environment:
                        - POSTGRES_DB=opbeans
                        - POSTGRES_PASSWORD=verysecure
                    ports:
                        - 5432:5432
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    volumes:
                        - ./docker/opbeans/sql:/docker-entrypoint-initdb.d
                        - pgdata:/var/lib/postgresql/data
                    healthcheck:
                        interval: 10s
                        test: ["CMD", "pg_isready", "-h", "postgres", "-U", "postgres"]""")
        )


class RedisServiceTest(ServiceTest):
    def test_redis(self):
        redis = Redis(version="6.2.4").render()
        self.assertEqual(
            redis, yaml.load("""
                redis:
                    image: redis:4
                    container_name: localtesting_6.2.4_redis
                    ports:
                      - 6379:6379
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    healthcheck:
                        interval: 10s
                        test: ["CMD", "redis-cli", "ping"]""")
        )


class ZookeeperServiceTest(ServiceTest):
    def test_zookeeper(self):
        zookeeper = Zookeeper(version="6.2.4").render()
        self.assertEqual(
            zookeeper, yaml.load("""
                zookeeper:
                    image: confluentinc/cp-zookeeper:latest
                    container_name: localtesting_6.2.4_zookeeper
                    environment:
                        ZOOKEEPER_CLIENT_PORT: 2181
                        ZOOKEEPER_TICK_TIME: 2000
                    ports:
                        - 127.0.0.1:2181:2181""")
        )


class LocalSetup(object):
    SUPPORTED_VERSIONS = {
        '6.0': '6.0.1',
        '6.1': '6.1.3',
        '6.2': '6.2.4',
        '6.3': '6.3.3',
        '6.4': '6.4.0',
        '6.5': '6.5.0',
        'master': '7.0.0-alpha1'
    }

    def __init__(self, argv=None, services=None):
        self.available_options = set()

        if services is None:
            services = discover_services()
        self.services = services

        parser = argparse.ArgumentParser(
            description="""
            This is a CLI for managing the local testing stack.
            Read the README.md for more information.
            """
        )

        # Add script version
        parser.add_argument(
            '-v',
            action='version',
            version='{0} v{1}'.format(PACKAGE_NAME, __version__)
        )

        # Add debug mode
        parser.add_argument(
            '--debug',
            help="Start in debug mode (more verbose)",
            action="store_const",
            dest="loglevel",
            const=logging.DEBUG,
            default=logging.INFO
        )

        subparsers = parser.add_subparsers(
            title='subcommands',
            description='Use one of the following commands:'
        )

        self.init_start_parser(
            subparsers.add_parser(
                'start',
                help="Start the stack. See `start --help` for options.",
                description="Main command for this script, starts the stack. Use the arguments to specify which "
                            "services to start. "
            ),
            services,
            argv=argv,
        ).set_defaults(func=self.start_handler)

        subparsers.add_parser(
            'status',
            help="Prints status of all services.",
            description="Prints the container status for each running service."
        ).set_defaults(func=self.status_handler)

        subparsers.add_parser(
            'load-dashboards',
            help="Loads APM dashbords into Kibana using APM Server.",
            description="Loads APM dashbords into Kibana using APM Server. APM Server, Elasticsearch, and Kibana must "
                        "be running. "
        ).set_defaults(func=self.dashboards_handler)

        subparsers.add_parser(
            'versions',
            help="Prints all running version numbers.",
            description="Prints version (and build) numbers of each running service."
        ).set_defaults(func=self.versions_handler)

        subparsers.add_parser(
            'stop',
            help="Stops all services.",
            description="Stops all running services and their containers."
        ).set_defaults(func=self.stop_handler)

        subparsers.add_parser(
            'list-options',
            help="Lists all available options.",
            description="Lists all available options (used for bash autocompletion)."
        ).set_defaults(func=self.listoptions_handler)

        self.init_sourcemap_parser(
            subparsers.add_parser(
                'upload-sourcemap',
                help="Uploads sourcemap to the APM Server"
            )
        ).set_defaults(func=self.upload_sourcemaps_handler)

        self.store_options(parser)

        self.args = parser.parse_args(argv)

        # py3
        if not hasattr(self.args, "func"):
            parser.error("command required")

    def set_docker_compose_path(self, dst):
        """override docker-compose-path argument, for tests"""
        self.args.__setattr__("docker_compose_path", dst)

    def __call__(self):
        self.args.func()

    def init_start_parser(self, parser, services, argv=None):
        if not argv:
            argv = sys.argv
        available_versions = ' / '.join(list(self.SUPPORTED_VERSIONS))
        help_text = (
                "Which version of the stack to start. " +
                "Available options: {0}".format(available_versions)
        )
        parser.add_argument("stack-version", action='store', help=help_text)

        # Add a --no-x / --with-x argument for each service, depending on default enabled/disabled
        # Slightly hackish: if we have an `--all` argument, use `--no-x` for all opbeans services
        has_all = '--all' in argv
        has_opbeans = has_all or any(o.startswith("--with-opbeans-") for o in argv)
        for service in services:
            if service.enabled() or \
                    (has_all and service.name().startswith('opbeans')) or \
                    (has_opbeans and service.name() in ('postgres', 'redis')):
                action = 'store_true'
                arg_prefix = '--no-'
                help_prefix = 'Disable '
            else:
                action = 'store_false'
                arg_prefix = '--with-'
                help_prefix = 'Enable '

            parser.add_argument(
                arg_prefix + service.name(),
                action=action,
                dest='disable_' + service.option_name(),
                help=help_prefix + service.name()
            )
            service.add_arguments(parser)

        # Add build candidate argument
        build_type_group = parser.add_mutually_exclusive_group()
        build_type_group.add_argument(
            '--bc',
            action='store',
            dest='bc',
            help='ID of the build candidate, e.g. 37b864a0',
            default=''
        )
        build_type_group.add_argument(
            '--release',
            action='store_true',
            dest='release',
            help='Use released version',
            default=False
        )
        build_type_group.add_argument(
            '--snapshot',
            action='store_false',
            dest='release',
            help='use snapshot version',
            default='',
        )

        # Add option to skip image downloads
        parser.add_argument(
            '--skip-download',
            action='store_true',
            dest='skip_download',
            help='Skip the download of fresh images and use current ones'
        )

        # option for path to docker-compose.yml
        parser.add_argument(
            '--docker-compose-path',
            type=argparse.FileType(mode='w'),
            default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')),
            help='path to docker-compose.yml'
        )

        # option to add a service and keep the rest running
        parser.add_argument(
            '--append',
            action='store_true',
            dest='append-service',
            help='Do not stop running services'
        )

        # Add image cache arguments
        parser.add_argument(
            '--image-cache-dir',
            default=os.path.abspath(os.path.join(os.path.dirname(__file__), '.images')),
            help='image cache directory',
        )

        parser.add_argument(
            '--force-build',
            action='store_true',
            help='force build of any images without docker cache',
            dest='force_build',
            default=False,
        )

        parser.add_argument(
            '--all',
            action='store_true',
            help='run all opbeans services',
            dest='run_all_opbeans',
            default=False,
        )

        parser.add_argument(
            '--oss',
            action='store_true',
            help='use oss container images',
            dest='oss',
            default=False,
        )

        parser.add_argument(
            '--opbeans-apm-server-url',
            action='store',
            help='server_url to use for Opbeans services',
            dest='opbeans_apm_server_url',
            default='http://apm-server:8200',
        )

        self.store_options(parser)

        return parser

    @staticmethod
    def init_sourcemap_parser(parser):
        parser.add_argument(
            '--sourcemap-file',
            action='store',
            dest='sourcemap_file',
            help='path to the sourcemap to upload. Defaults to first map found in node/sourcemaps directory',
            default=''
        )

        parser.add_argument(
            '--server-url',
            action='store',
            dest='server_url',
            help='URL of the apm-server. Defaults to running apm-server container, if any',
            default=''
        )

        parser.add_argument(
            '--service-name',
            action='store',
            dest='service_name',
            help='Name of the frontend app. Defaults to "opbeans-react"',
            default='opbeans-react'
        )

        parser.add_argument(
            '--service-version',
            action='store',
            dest='service_version',
            help='Version of the frontend app. Defaults to the BUILDDATE env variable of the "opbeans-node" container',
            default=''
        )

        parser.add_argument(
            '--bundle-path',
            action='store',
            dest='bundle_path',
            help='Bundle path in minified files. Defaults to "http://opbeans-node:3000/static/js/" + name of sourcemap',
            default=''
        )

        parser.add_argument(
            '--secret-token',
            action='store',
            dest='secret_token',
            help='Secret token to authenticate against the APM server. Empty by default.',
            default=''
        )

        return parser

    def store_options(self, parser):
        """
        Helper method to extract and store all arguments
        in a list of all possible arguments.
        Used for bash tab completion.
        """
        # Run through all parser actions
        for action in parser._actions:
            for option in action.option_strings:
                self.available_options.add(option)

        # Get subparsers from parser
        subparsers_actions = [
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]

        # Run through all subparser actions
        for subparsers_action in subparsers_actions:
            for choice, subparser in subparsers_action.choices.items():
                self.available_options.add(choice)

    #
    # handlers
    #
    @staticmethod
    def dashboards_handler():
        cmd = (
                'docker ps --filter "name=kibana" -q | xargs docker inspect ' +
                '-f \'{{ index .Config.Labels "co.elatic.apm.stack-version" }}\''
        )

        # Check if Docker is running and get running containers
        try:
            running_version = subprocess.check_output(cmd, shell=True).decode('utf8').strip()
        except subprocess.CalledProcessError:
            # If not, exit immediately
            print('Make sure Docker is running before running this script.')
            sys.exit(1)

        # Check for empty result
        if running_version == "":
            print('No containers are running.')
            print('Make sure the stack is running before importing dashboards.')
            sys.exit(1)

        # Prepare and call command
        print("Loading Kibana dashboards using APM Server:\n")
        cmd = (
                'docker-compose run --rm ' +
                'apm-server -e setup -E setup.kibana.host="kibana:5601"'
        )
        subprocess.call(cmd, shell=True)

    def listoptions_handler(self):
        print("{}".format(" ".join(self.available_options)))

    def start_handler(self):
        args = vars(self.args)

        if "version" not in args:
            # use stack-version directly if not supported, to allow use of specific releases, eg 6.2.3
            args["version"] = self.SUPPORTED_VERSIONS.get(args["stack-version"], args["stack-version"])

        selections = set()
        for service in self.services:
            if not args.get("disable_" + service.option_name()):
                selections.add(service(**args))

        # `docker load` images if necessary
        # need should mostly go away once snapshot builds are available a docker registry
        if not args["skip_download"]:
            images_to_load = {service.image_download_url() for service in selections} - {None}
            if images_to_load:
                load_images(images_to_load, args["image_cache_dir"])

        # generate docker-compose.yml
        services = {}
        for service in selections:
            services.update(service.render())
        compose = dict(
            version="2.1",
            services=services,
            networks=dict(
                default={"name": "apm-integration-testing"},
            ),
            volumes=dict(
                esdata={"driver": "local"},
                pgdata={"driver": "local"},
            ),
        )
        docker_compose_path = args["docker_compose_path"]
        json.dump(compose, docker_compose_path, indent=2, sort_keys=True)
        docker_compose_path.flush()

        # try to figure out if writing to a real file, not amazing
        if hasattr(docker_compose_path, "name") and os.path.isdir(os.path.dirname(docker_compose_path.name)):
            docker_compose_path.close()
            print("Starting stack services..\n")

            # always build if possible, should be quick for rebuilds
            if any("build" in service for service in compose["services"].values()):
                docker_compose_build = ["docker-compose", "-f", docker_compose_path.name, "build", "--pull"]
                if args["force_build"]:
                    docker_compose_build.append("--no-cache")
                subprocess.call(docker_compose_build)

            # really start
            docker_compose_up = ["docker-compose", "-f", docker_compose_path.name, "up", "-d"]
            subprocess.call(docker_compose_up)

    @staticmethod
    def status_handler():
        print("Status for all services:\n")
        subprocess.call(['docker-compose', 'ps'])

    @staticmethod
    def stop_handler():
        print("Stopping all stack services..\n")
        subprocess.call(['docker-compose', 'stop'])

    def upload_sourcemaps_handler(self):
        server_url = self.args.server_url
        sourcemap_file = self.args.sourcemap_file
        bundle_path = self.args.bundle_path
        service_version = self.args.service_version
        if not server_url:
            cmd = 'docker ps --filter "name=apm-server" -q | xargs docker port | grep "8200/tcp"'
            try:
                port_desc = subprocess.check_output(cmd, shell=True).decode('utf8').strip()
            except subprocess.CalledProcessError:
                print("No running apm-server found. Start it, or provide a server url with --server-url")
                sys.exit(1)
            server_url = 'http://' + port_desc.split(' -> ')[1]
        if sourcemap_file:
            sourcemap_file = os.path.expanduser(sourcemap_file)
            if not os.path.exists(sourcemap_file):
                print('{} not found. Try again :)'.format(sourcemap_file))
                sys.exit(1)
        else:
            try:
                sourcemap_file = glob.glob('./node/sourcemaps/*.map')[0]
            except IndexError:
                print(
                    'No source map found in ./node/sourcemaps.\n'
                    'Start the opbeans-node container, it will create one automatically.'
                )
                sys.exit(1)
        if not bundle_path:
            bundle_path = 'http://opbeans-node:3000/static/js/' + os.path.basename(sourcemap_file)
        if not service_version:
            cmd = (
                'docker ps --filter "name=opbeans-node" -q | '
                'xargs docker inspect -f \'{{range .Config.Env}}{{println .}}{{end}}\' | '
                'grep ELASTIC_APM_JS_BASE_SERVICE_VERSION'
            )
            try:
                build_date = subprocess.check_output(cmd, shell=True).decode('utf8').strip()
                service_version = build_date.split("=")[1]
            except subprocess.CalledProcessError:
                print("opbeans-node container not found. Start it or set --service-version")
                sys.exit(1)
        if self.args.secret_token:
            auth_header = '-H "Authorization: Bearer {}" '.format(self.args.secret_token)
        else:
            auth_header = ''
        print("Uploading {} to {}".format(sourcemap_file, server_url))
        cmd = (
            'curl -X POST '
            '-F service_name="{service_name}" '
            '-F service_version="{service_version}" '
            '-F bundle_filepath="{bundle_path}" '
            '-F sourcemap=@{sourcemap_file} '
            '{auth_header}'
            '{server_url}/v1/client-side/sourcemaps'
        ).format(
            service_name=self.args.service_name,
            service_version=service_version,
            bundle_path=bundle_path,
            sourcemap_file=sourcemap_file,
            auth_header=auth_header,
            server_url=server_url,
        )
        subprocess.check_output(cmd, shell=True).decode('utf8').strip()

    @staticmethod
    def versions_handler():
        Container = collections.namedtuple(
            'Container', ('service', 'stack_version', 'created')
        )
        cmd = (
            'docker ps --filter "name=localtesting" -q | xargs docker inspect '
            '-f \'{{ index .Config.Labels "co.elatic.apm.stack-version" }}\\t{{ .Image }}\\t{{ .Name }}\''
        )

        # Check if Docker is running and get running containers
        try:
            labels = subprocess.check_output(cmd, shell=True).decode('utf8').strip()
            lines = [line.split('\\t') for line in labels.split('\n') if line.split('\\t')[0]]
            for line in lines:
                line[1] = subprocess.check_output(
                    ['docker', 'inspect', '-f', '{{ .Created }}', line[1]]
                ).decode('utf8').strip()
            running_versions = {c.service: c for c in (Container(
                line[2].split('_')[-1],
                line[0],
                datetime.datetime.strptime(line[1].split('.')[0], "%Y-%m-%dT%H:%M:%S")
            ) for line in lines)}
        except subprocess.CalledProcessError:
            # If not, exit immediately
            print('Make sure Docker is running before running this script.')
            sys.exit(1)

        # Check for empty result
        if not running_versions:
            print('No containers are running.')
            print('Make sure the stack is running before checking versions.')
            sys.exit(1)

        # Run all version checks
        print('Getting current version numbers for services...')

        def run_container_command(name, cmd):
            # Get id from docker-compose
            container_id = subprocess.check_output('docker-compose ps -q {}'.format(name),
                                                   shell=True).decode('utf8').strip()

            # Prepare exec command
            command = 'docker exec -it {0} {1}'.format(container_id, cmd)

            # Run command
            try:
                output = subprocess.check_output(
                    command, stderr=open(os.devnull, 'w'), shell=True).decode('utf8').strip()
            except subprocess.CalledProcessError:
                # Handle errors
                print('\tContainer "{}" is not running or an error occurred'.format(name))
                return False

            return output

        def print_elasticsearch_version(container):
            print("\nElasticsearch (image built: %s UTC):" % container.created)

            version = run_container_command(
                'elasticsearch', './bin/elasticsearch --version'
            )

            if version:
                print("\t{0}".format(version))

        def print_apmserver_version(container):
            print("\nAPM Server (image built: %s UTC):" % container.created)

            version = run_container_command('apm-server', 'apm-server version')

            if version:
                print("\t{0}".format(version))

        def print_kibana_version(container):
            print("\nKibana (image built: %s UTC):" % container.created)

            package_json = run_container_command('kibana', 'cat package.json')

            if package_json:

                # Try to parse package.json
                try:
                    data = json.loads(package_json)
                except ValueError as e:
                    print('ERROR: Could not parse Kibana\'s package.json file.')
                    return e

                print("\tVersion: {}".format(data['version']))
                print("\tBranch: {}".format(data['branch']))
                print("\tBuild SHA: {}".format(data['build']['sha']))
                print("\tBuild number: {}".format(data['build']['number']))

        def print_opbeansnode_version(_):
            print("\nAgent version (in opbeans-node):")

            version = run_container_command(
                'opbeans-node', 'npm list | grep elastic-apm-node'
            )

            if version:
                version = version.replace('+-- elastic-apm-node@', '')
                print("\t{0}".format(version))

        def print_opbeanspython_version(_):
            print("\nAgent version (in opbeans-python):")

            version = run_container_command(
                'opbeans-python', 'pip freeze | grep elastic-apm'
            )

            if version:
                version = version.replace('elastic-apm==', '')
                print("\t{0}".format(version))

        def print_opbeansruby_version(_):
            print("\nAgent version (in opbeans-ruby):")

            version = run_container_command(
                'opbeans-ruby', 'gem list | grep elastic-apm'
            )

            if version:
                version = version.replace('elastic-apm (*+)', '\1')
                print("\t{0}".format(version))

        dispatch = {
            'apm-server': print_apmserver_version,
            'elasticsearch': print_elasticsearch_version,
            'kibana': print_kibana_version,
            'opbeans-node': print_opbeansnode_version,
            'opbeans-python': print_opbeanspython_version,
            'opbeans-ruby': print_opbeansruby_version,
        }
        for service_name, container in running_versions.items():
            print_version = dispatch.get(service_name)
            if not print_version:
                print("unknown version for", service_name)
                continue
            print_version(container)


#
# Local setup tests
#
class LocalTest(unittest.TestCase):
    maxDiff = None

    def test_service_registry(self):
        registry = discover_services()
        self.assertIn(ApmServer, registry)

    @mock.patch(__name__ + ".load_images")
    def test_start_6_2_default(self, mock_load_images):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'6.2': '6.2.10'}):
            setup = LocalSetup(
                argv=["start", "6.2", "--docker-compose-path", "-", "--image-cache-dir", image_cache_dir])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        want = yaml.load("""
        version: '2.1'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_6.2.10_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://apm-server:8200/healthcheck']
                image: docker.elastic.co/apm/apm-server:6.2.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060']

            elasticsearch:
                container_name: localtesting_6.2.10_elasticsearch
                environment: [cluster.name=docker-cluster, bootstrap.memory_lock=true, discovery.type=single-node, 'ES_JAVA_OPTS=-Xms1g -Xmx1g', path.data=/usr/share/elasticsearch/data/6.2.10, xpack.security.enabled=false, xpack.license.self_generated.type=trial]
                healthcheck:
                    interval: '20'
                    retries: 10
                    test: [CMD-SHELL, 'curl -s http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch-platinum:6.2.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                mem_limit: 5g
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: ['esdata:/usr/share/elasticsearch/data']

            kibana:
                container_name: localtesting_6.2.10_kibana
                depends_on:
                    elasticsearch: {condition: service_healthy}
                environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200', SERVER_NAME: kibana.example.org, XPACK_MONITORING_ENABLED: 'true'}
                healthcheck:
                    interval: 5s
                    retries: 20
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://kibana:5601/']
                image: docker.elastic.co/kibana/kibana-x-pack:6.2.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
        networks:
            default: {name: apm-integration-testing}
        volumes:
            esdata: {driver: local}
            pgdata: {driver: local}
        """)  # noqa: 501
        self.assertDictEqual(got, want)
        mock_load_images.assert_called_once_with(
            {
                "https://snapshots.elastic.co/docker/apm-server-6.2.10-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/elasticsearch-platinum-6.2.10-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/kibana-x-pack-6.2.10-SNAPSHOT.tar.gz",
            },
            image_cache_dir)

    @mock.patch(__name__ + '.load_images')
    def test_start_6_3_default(self, mock_load_images):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'6.3': '6.3.10'}):
            setup = LocalSetup(
                argv=["start", "6.3", "--docker-compose-path", "-", "--image-cache-dir", image_cache_dir])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        want = yaml.load("""
        version: '2.1'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_6.3.10_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://apm-server:8200/healthcheck']
                image: docker.elastic.co/apm/apm-server:6.3.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.3.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060']

            elasticsearch:
                container_name: localtesting_6.3.10_elasticsearch
                environment: [cluster.name=docker-cluster, bootstrap.memory_lock=true, discovery.type=single-node, 'ES_JAVA_OPTS=-Xms1g -Xmx1g', path.data=/usr/share/elasticsearch/data/6.3.10, xpack.security.enabled=false, xpack.license.self_generated.type=trial, xpack.monitoring.collection.enabled=true]
                healthcheck:
                    interval: '20'
                    retries: 10
                    test: [CMD-SHELL, 'curl -s http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch:6.3.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.3.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                mem_limit: 5g
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: ['esdata:/usr/share/elasticsearch/data']

            kibana:
                container_name: localtesting_6.3.10_kibana
                depends_on:
                    elasticsearch: {condition: service_healthy}
                environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200', SERVER_NAME: kibana.example.org, XPACK_MONITORING_ENABLED: 'true', XPACK_XPACK_MAIN_TELEMETRY_ENABLED: 'false'}
                healthcheck:
                    interval: 5s
                    retries: 20
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://kibana:5601/']
                image: docker.elastic.co/kibana/kibana:6.3.10-SNAPSHOT
                labels: [co.elatic.apm.stack-version=6.3.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
        networks:
            default: {name: apm-integration-testing}
        volumes:
            esdata: {driver: local}
            pgdata: {driver: local}
        """)  # noqa: 501
        self.assertDictEqual(got, want)
        mock_load_images.assert_called_once_with(
            {
                "https://snapshots.elastic.co/docker/apm-server-6.3.10-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/elasticsearch-6.3.10-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/kibana-6.3.10-SNAPSHOT.tar.gz",
            },
            image_cache_dir)

    @mock.patch(__name__ + '.load_images')
    def test_start_master_default(self, mock_load_images):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '7.0.10-alpha1'}):
            setup = LocalSetup(
                argv=["start", "master", "--docker-compose-path", "-", "--image-cache-dir", image_cache_dir])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        want = yaml.load("""
        version: '2.1'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_7.0.10-alpha1_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://apm-server:8200/healthcheck']
                image: docker.elastic.co/apm/apm-server:7.0.10-alpha1-SNAPSHOT
                labels: [co.elatic.apm.stack-version=7.0.10-alpha1]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060']

            elasticsearch:
                container_name: localtesting_7.0.10-alpha1_elasticsearch
                environment: [cluster.name=docker-cluster, bootstrap.memory_lock=true, discovery.type=single-node, 'ES_JAVA_OPTS=-Xms1g -Xmx1g -XX:UseAVX=2', path.data=/usr/share/elasticsearch/data/7.0.10-alpha1, xpack.security.enabled=false, xpack.license.self_generated.type=trial, xpack.monitoring.collection.enabled=true]
                healthcheck:
                    interval: '20'
                    retries: 10
                    test: [CMD-SHELL, 'curl -s http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch:7.0.10-alpha1-SNAPSHOT
                labels: [co.elatic.apm.stack-version=7.0.10-alpha1]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                mem_limit: 5g
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: ['esdata:/usr/share/elasticsearch/data']

            kibana:
                container_name: localtesting_7.0.10-alpha1_kibana
                depends_on:
                    elasticsearch: {condition: service_healthy}
                environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200', SERVER_NAME: kibana.example.org, XPACK_MONITORING_ENABLED: 'true', XPACK_XPACK_MAIN_TELEMETRY_ENABLED: 'false'}
                healthcheck:
                    interval: 5s
                    retries: 20
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://kibana:5601/']
                image: docker.elastic.co/kibana/kibana:7.0.10-alpha1-SNAPSHOT
                labels: [co.elatic.apm.stack-version=7.0.10-alpha1]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
        networks:
            default: {name: apm-integration-testing}
        volumes:
            esdata: {driver: local}
            pgdata: {driver: local}
        """)  # noqa: 501
        self.assertDictEqual(got, want)
        mock_load_images.assert_called_once_with(
            {
                "https://snapshots.elastic.co/docker/apm-server-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/elasticsearch-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/kibana-7.0.10-alpha1-SNAPSHOT.tar.gz",
            },
            image_cache_dir)

    @mock.patch(__name__ + '.load_images')
    def test_start_master_custom_images(self, mock_load_images):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '7.0.10-alpha1'}):
            setup = LocalSetup(
                argv=["start", "master", "--docker-compose-path", "-", "--image-cache-dir", image_cache_dir,
                      "--apm-server-version", "6.3.15", "--kibana-oss"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)

        self.assertEqual(
            "docker.elastic.co/apm/apm-server:6.3.15-SNAPSHOT",
            got["services"]["apm-server"]["image"]
        )
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch:7.0.10-alpha1-SNAPSHOT",
            got["services"]["elasticsearch"]["image"]
        )
        self.assertEqual(
            "docker.elastic.co/kibana/kibana-oss:7.0.10-alpha1-SNAPSHOT",
            got["services"]["kibana"]["image"]
        )
        mock_load_images.assert_called_once_with(
            {
                "https://snapshots.elastic.co/docker/apm-server-6.3.15-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/elasticsearch-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/kibana-oss-7.0.10-alpha1-SNAPSHOT.tar.gz",
            },
            image_cache_dir)

    @mock.patch(__name__ + '.load_images')
    def test_start_master_with_logstash_and_metricbeat(self, mock_load_images):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '7.0.10-alpha1'}):
            setup = LocalSetup(
                argv=["start", "master", "--docker-compose-path", "-", "--image-cache-dir", image_cache_dir,
                      "--with-logstash", "--with-metricbeat"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        mock_load_images.assert_called_once_with(
            {
                "https://snapshots.elastic.co/docker/apm-server-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/elasticsearch-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/kibana-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/logstash-7.0.10-alpha1-SNAPSHOT.tar.gz",
                "https://snapshots.elastic.co/docker/metricbeat-7.0.10-alpha1-SNAPSHOT.tar.gz",
            },
            image_cache_dir)

    @mock.patch(__name__ + '.load_images')
    def test_start_all(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        setup = LocalSetup(
            argv=["start", "master", "--all",
                  "--docker-compose-path", "-"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        services = got["services"]
        self.assertIn("redis", services)
        self.assertIn("postgres", services)

    @mock.patch(__name__ + '.load_images')
    def test_start_one_opbeans(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        setup = LocalSetup(
            argv=["start", "master", "--with-opbeans-node",
                  "--docker-compose-path", "-"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        services = got["services"]
        self.assertIn("redis", services)
        self.assertIn("postgres", services)

    @mock.patch(__name__ + '.load_images')
    def test_start_opbeans_no_apm_server(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        setup = LocalSetup(
            argv=["start", "master", "--all", "--no-apm-server",
                  "--docker-compose-path", "-"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        depends_on = set(got["services"]["opbeans-node"]["depends_on"].keys())
        self.assertSetEqual({"postgres", "redis"}, depends_on)
        depends_on = set(got["services"]["opbeans-python"]["depends_on"].keys())
        self.assertSetEqual({"elasticsearch", "postgres", "redis"}, depends_on)
        depends_on = set(got["services"]["opbeans-ruby"]["depends_on"].keys())
        self.assertSetEqual({"elasticsearch", "postgres", "redis"}, depends_on)
        for name, service in got["services"].items():
            self.assertNotIn("apm-server", service.get("depends_on", {}), "{} depends on apm-server".format(name))

    @mock.patch(__name__ + '.load_images')
    def test_start_unsupported_version_pre_6_3(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        version = "1.2.3"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(
            argv=["start", version, "--docker-compose-path", "-", "--release"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch-platinum:{}".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana-x-pack:{}".format(version), services["kibana"]["image"])

    @mock.patch(__name__ + '.load_images')
    def test_start_unsupported_version(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        version = "6.9.5"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(
            argv=["start", version, "--docker-compose-path", "-"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch:{}-SNAPSHOT".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana:{}-SNAPSHOT".format(version), services["kibana"]["image"])

    def test_docker_download_image_url(self):
        Case = collections.namedtuple("Case", ("service", "expected", "args"))
        common_args = (("image_cache_dir", ".images"),)
        cases = [
            # pre-6.3
            Case(ApmServer, "https://snapshots.elastic.co/docker/apm-server-6.2.10-SNAPSHOT.tar.gz",
                 dict(version="6.2.10")),
            Case(Elasticsearch, "https://snapshots.elastic.co/docker/elasticsearch-platinum-6.2.10-SNAPSHOT.tar.gz",
                 dict(version="6.2.10")),
            Case(Kibana, "https://snapshots.elastic.co/docker/kibana-x-pack-6.2.10-SNAPSHOT.tar.gz",
                 dict(version="6.2.10")),
            # post-6.3
            Case(ApmServer, "https://snapshots.elastic.co/docker/apm-server-6.3.10-SNAPSHOT.tar.gz",
                 dict(version="6.3.10")),
            Case(Elasticsearch, "https://staging.elastic.co/6.3.10-be84d930/docker/elasticsearch-6.3.10.tar.gz",
                 dict(bc="be84d930", version="6.3.10")),
            Case(Elasticsearch, "https://staging.elastic.co/6.3.10-be84d930/docker/elasticsearch-oss-6.3.10.tar.gz",
                 dict(bc="be84d930", oss=True, version="6.3.10")),
            Case(Elasticsearch, "https://snapshots.elastic.co/docker/elasticsearch-6.3.10-SNAPSHOT.tar.gz",
                 dict(version="6.3.10")),
            Case(Elasticsearch, "https://snapshots.elastic.co/docker/elasticsearch-oss-6.3.10-SNAPSHOT.tar.gz",
                 dict(oss=True, version="6.3.10")),
            Case(Kibana, "https://snapshots.elastic.co/docker/kibana-6.3.10-SNAPSHOT.tar.gz",
                 dict(version="6.3.10")),
        ]
        for case in cases:
            args = dict(common_args)
            if case.args:
                args.update(case.args)
            service = case.service(**args)
            got = service.image_download_url()
            self.assertEqual(case.expected, got)

    def test_parse(self):
        cases = [
            ("6.3", [6, 3]),
            ("6.3.0", [6, 3, 0]),
            ("6.3.1", [6, 3, 1]),
            ("6.3.10", [6, 3, 10]),
            ("6.3.10-alpha1", [6, 3, 10]),
        ]
        for ver, want in cases:
            got = parse_version(ver)
            self.assertEqual(want, got)


def main():
    # Enable logging
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup = LocalSetup(sys.argv[1:])
    setup()


if __name__ == '__main__':
    main()
