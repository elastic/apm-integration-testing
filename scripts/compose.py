#!/usr/bin/env python
"""
CLI for starting a testing environment using docker-compose.
"""
from __future__ import print_function

from abc import abstractmethod

import argparse
import codecs
import collections
from collections import OrderedDict
import datetime
import functools
import glob
import inspect
import json
import logging
import multiprocessing
import os
import re
import sys
import subprocess

try:
    from urllib.request import urlopen, urlretrieve, Request
except ImportError:
    from urllib import urlretrieve
    from urllib2 import urlopen, Request

#
# package info
#
PACKAGE_NAME = 'localmanager'
__version__ = "4.0.0"

DEFAULT_STACK_VERSION = "8.0"
DEFAULT_APM_SERVER_URL = "http://apm-server:8200"
DEFAULT_APM_JS_SERVER_URL = "http://localhost:8200"


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


DEFAULT_HEALTHCHECK_INTERVAL = "10s"
DEFAULT_HEALTHCHECK_RETRIES = 12


def curl_healthcheck(port, host="localhost", path="/healthcheck",
                     interval=DEFAULT_HEALTHCHECK_INTERVAL, retries=DEFAULT_HEALTHCHECK_RETRIES):
    return {
        "interval": interval,
        "retries": retries,
        "test": ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent",
                 "--output", "/dev/null",
                 "http://{}:{}{}".format(host, port, path)]
    }


build_manifests = {}  # version -> manifest cache


def latest_build_manifest(version):
    minor_version = ".".join(version.split(".", 2)[:2])
    rsp = urlopen("https://staging.elastic.co/latest/{}.json".format(minor_version))
    if rsp.code != 200:
        raise Exception("failed to query build candidates at {}: {}".format(rsp.geturl(), rsp.info()))
    encoding = "utf-8"  # python2 rsp.headers.get_content_charset("utf-8")
    info = json.load(codecs.getreader(encoding)(rsp))
    if "summary_url" in info:
        print("found latest build candidate for {} - {} at {}".format(minor_version, info["summary_url"], rsp.geturl()))
    return info["manifest_url"]


def resolve_bc(version, build_id):
    """construct or discover build candidate manifest url"""
    if build_id is None:
        return

    if version is None:
        return

    # check cache
    if version in build_manifests:
        return build_manifests[version]

    if build_id == "latest":
        manifest_url = latest_build_manifest(version)
    else:
        manifest_url = "https://staging.elastic.co/{patch_version}-{sha}/manifest-{patch_version}.json".format(
            patch_version=version,
            sha=build_id,
        )
    rsp = urlopen(manifest_url)
    if rsp.code != 200:
        raise Exception("failed to fetch build manifest at {}: {}".format(rsp.geturl(), rsp.info()))
    encoding = "utf-8"  # python2 rsp.headers.get_content_charset("utf-8")
    manifest = json.load(codecs.getreader(encoding)(rsp))
    build_manifests[version] = manifest  # fill cache
    return manifest


def parse_version(version):
    res = []
    for x in version.split('.'):
        try:
            y = int(x)
        except ValueError:
            y = int(x.split("-", 1)[0])
        res.append(y)
    return res


def add_agent_environment(mappings):
    def fn(func):
        def add_content(self):
            content = func(self)
            for option, envvar in sorted(mappings):
                val = self.options.get(option)
                if val is not None:
                    if isinstance(content["environment"], dict):
                        content["environment"][envvar] = val
                    else:
                        content["environment"].append(envvar + "=" + val)
            return content
        return add_content
    return fn


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


#
# Elastic Services
#
class ApmServer(StackService, Service):
    docker_path = "apm"

    SERVICE_PORT = "8200"
    DEFAULT_MONITOR_PORT = "6060"
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "file", "kafka", "logstash"}
    DEFAULT_KIBANA_HOST = "kibana:5601"

    def __init__(self, **options):
        super(ApmServer, self).__init__(**options)

        v1_rate_limit = ("apm-server.frontend.rate_limit", "100000")
        if self.at_least_version("6.5"):
            rum_config = [
                ("apm-server.rum.enabled", "true"),
                ("apm-server.rum.event_rate.limit", "1000"),
            ]
            if not self.at_least_version("7.0"):
                rum_config.append(v1_rate_limit)
        else:
            rum_config = [
                ("apm-server.frontend.enabled", "true"),
                v1_rate_limit,
            ]

        self.apm_server_command_args = rum_config
        self.apm_server_command_args.extend([
            ("apm-server.host", "0.0.0.0:8200"),
            ("apm-server.read_timeout", "1m"),
            ("apm-server.shutdown_timeout", "2m"),
            ("apm-server.write_timeout", "1m"),
            ("logging.json", "true"),
            ("logging.metrics.enabled", "false"),
            ("setup.kibana.host", self.DEFAULT_KIBANA_HOST),
            ("setup.template.settings.index.number_of_replicas", "0"),
            ("setup.template.settings.index.number_of_shards", "1"),
            ("setup.template.settings.index.refresh_interval", "1ms"),
            ("xpack.monitoring.elasticsearch", "true"),
            ("xpack.monitoring.enabled", "true")
        ])
        if options.get("apm_server_self_instrument"):
            self.apm_server_command_args.append(("apm-server.instrumentation.enabled", "true"))
        self.depends_on = {"elasticsearch": {"condition": "service_healthy"}} if options.get(
            "enable_elasticsearch", True) else {}
        self.build = self.options.get("apm_server_build")

        if self.options.get("apm_server_ilm_disable"):
            self.apm_server_command_args.append(("apm-server.ilm.enabled", "false"))
        elif self.at_least_version("7.2") and not self.at_least_version("7.3") and not self.oss:
            self.apm_server_command_args.append(("apm-server.ilm.enabled", "true"))

        if self.options.get("apm_server_acm_disable"):
            self.apm_server_command_args.append(("apm-server.kibana.enabled", "false"))
        elif self.at_least_version("7.3"):
            self.apm_server_command_args.extend([
                ("apm-server.kibana.enabled", "true"),
                ("apm-server.kibana.host", self.DEFAULT_KIBANA_HOST)])

        if self.options.get("enable_kibana", True):
            self.depends_on["kibana"] = {"condition": "service_healthy"}
            if options.get("apm_server_dashboards", True) and not self.at_least_version("7.0") \
                    and not self.options.get("xpack_secure"):
                self.apm_server_command_args.append(
                    ("setup.dashboards.enabled", "true")
                )

        if self.options.get("apm_server_secret_token"):
            self.apm_server_command_args.append(("apm-server.secret_token", self.options["apm_server_secret_token"]))

        self.apm_server_monitor_port = options.get("apm_server_monitor_port", self.DEFAULT_MONITOR_PORT)
        self.apm_server_output = options.get("apm_server_output", self.DEFAULT_OUTPUT)

        if options.get("apm_server_queue", "mem") == "file":
            # enable file spool queue
            q = {"file": {"path": "$${path.data}/spool.dat"}, "write": {}}
            # override defaults
            if options.get("apm_server_queue_file_size"):
                q["file"]["size"] = options["apm_server_queue_file_size"]
            if options.get("apm_server_queue_file_page_size"):
                q["file"]["page_size"] = options["apm_server_queue_file_page_size"]
            if options.get("apm_server_queue_write_buffer_size"):
                q["write"]["buffer_size"] = options["apm_server_queue_write_buffer_size"]
            if options.get("apm_server_queue_write_flush_events"):
                q["write"]["flush.events"] = options["apm_server_queue_write_flush_events"]
            if options.get("apm_server_queue_write_flush_timeout"):
                q["write"]["flush.timeout"] = options["apm_server_queue_write_flush_timeout"]
            if not q["write"]:
                q.pop("write")
            self.apm_server_command_args.append(("queue.spool", json.dumps(q)))

        es_urls = []

        def add_es_config(args, prefix="output"):
            """add elasticsearch configuration options."""
            default_apm_server_creds = {"username": "apm_server_user", "password": "changeme"}
            args.append((prefix + ".elasticsearch.hosts", json.dumps(es_urls)))
            for cfg in ("username", "password"):
                es_opt = "apm_server_elasticsearch_{}".format(cfg)
                if self.options.get(es_opt):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), self.options[es_opt]))
                elif self.options.get("xpack_secure"):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), default_apm_server_creds.get(cfg)))

        es_urls = self.options.get("apm_server_elasticsearch_urls") or [self.DEFAULT_ELASTICSEARCH_HOSTS]

        if self.apm_server_output == "elasticsearch":
            add_es_config(self.apm_server_command_args)
            self.apm_server_command_args.extend([
                ("output.elasticsearch.enabled", "true"),
            ])
            if options.get("apm_server_enable_pipeline", True) and self.at_least_version("6.5"):
                pipeline_name = "apm" if self.at_least_version("7.2") else "apm_user_agent"
                self.apm_server_command_args.extend([
                    ("output.elasticsearch.pipelines", "[{pipeline: '%s'}]" % pipeline_name),
                    ("apm-server.register.ingest.pipeline.enabled", "true"),
                ])
        else:
            add_es_config(self.apm_server_command_args, prefix="xpack.monitoring")
            self.apm_server_command_args.extend([
                ("output.elasticsearch.enabled", "false"),
            ])
            if self.apm_server_output == "kafka":
                self.apm_server_command_args.extend([
                    ("output.kafka.enabled", "true"),
                    ("output.kafka.hosts", "[\"kafka:9092\"]"),
                    ("output.kafka.topics", "[{default: 'apm', topic: 'apm-%{[service.name]}'}]"),
                ])
            elif self.apm_server_output == "logstash":
                self.apm_server_command_args.extend([
                    ("output.logstash.enabled", "true"),
                    ("output.logstash.hosts", "[\"logstash:5044\"]"),
                ])
            elif self.apm_server_output == "file":
                self.apm_server_command_args.extend([
                    ("output.file.enabled", "true"),
                    ("output.file.path", self.options.get("apm_server_output_file", os.devnull)),
                ])

        for opt in options.get("apm_server_opt", []):
            self.apm_server_command_args.append(opt.split("=", 1))

        self.apm_server_count = options.get("apm_server_count", 1)
        apm_server_record = options.get("apm_server_record", False)
        self.apm_server_tee = options.get("apm_server_tee") or apm_server_record  # tee if requested or if recording
        if self.apm_server_tee:
            # convenience for tee without count
            if self.apm_server_count == 1:
                self.apm_server_count = 2
            if apm_server_record:
                self.apm_server_tee_build = {
                    "context": "docker/apm-server/recorder",
                }
            else:
                # always build 8.0
                self.apm_server_tee_build = {
                    "args": {
                        "apm_server_base_image": "docker.elastic.co/apm/apm-server:8.0.0-SNAPSHOT",
                        "apm_server_branch": "master",
                        "apm_server_repo": "https://github.com/elastic/apm-server.git"
                    },
                    "context": "docker/apm-server"
                }

    @classmethod
    def add_arguments(cls, parser):
        super(ApmServer, cls).add_arguments(parser)
        parser.add_argument(
            '--apm-server-build',
            const="https://github.com/elastic/apm-server.git",
            nargs="?",
            help='build apm-server from a git repo[@branch|sha], eg https://github.com/elastic/apm-server.git@v2'
        )
        parser.add_argument(
            "--apm-server-ilm-disable",
            action="store_true",
            help='disable ILM (enabled by default in 7.2+)'
        )
        parser.add_argument(
            '--apm-server-output',
            choices=cls.OUTPUTS,
            default='elasticsearch',
            help='apm-server output'
        )
        parser.add_argument(
            '--apm-server-output-file',
            default=os.devnull,
            help='apm-server output path (when output=file)'
        )
        parser.add_argument(
            "--no-apm-server-pipeline",
            action="store_false",
            dest="apm_server_enable_pipeline",
            help='disable apm-server pipelines.'
        )
        parser.add_argument(
            "--no-apm-server-self-instrument",
            action="store_false",
            dest="apm_server_self_instrument",
            help='disable apm-server self instrumentation.'
        )
        parser.add_argument(
            '--apm-server-count',
            type=int,
            default=1,
            help="apm-server count. >1 adds a load balancer service to distribute traffic between servers.",
        )
        parser.add_argument(
            '--apm-server-elasticsearch-url',
            action="append",
            dest="apm_server_elasticsearch_urls",
            help="apm-server elasticsearch output url(s)."
        )
        parser.add_argument(
            '--apm-server-elasticsearch-username',
            help="apm-server elasticsearch output username.",
        )
        parser.add_argument(
            '--apm-server-elasticsearch-password',
            help="apm-server elasticsearch output password.",
        )
        parser.add_argument(
            "--apm-server-queue",
            choices=("file", "mem"),
            default="mem",
            help="apm-server queue type.",
        )
        parser.add_argument(
            "--apm-server-queue-file-size",
            help="apm-server file spool size (eg 128MiB).",
        )
        parser.add_argument(
            "--apm-server-queue-file-page-size",
            help="apm-server file spool page size (eg 16KiB).",
        )
        parser.add_argument(
            "--apm-server-queue-write-buffer-size",
            help="apm-server file write buffer size (eg 10MiB).",
        )
        parser.add_argument(
            "--apm-server-queue-write-codec",
            choices=("cbor", "json"),
            default="cbor",
            help="apm-server file write codec.",
        )
        parser.add_argument(
            "--apm-server-queue-write-flush-events",
            help="apm-server file write flush event count.",
        )
        parser.add_argument(
            "--apm-server-queue-write-flush-timeout",
            help="apm-server file write flush timeout.",
        )
        parser.add_argument(
            '--apm-server-secret-token',
            dest="apm_server_secret_token",
            help="apm-server secret token.",
        )
        parser.add_argument(
            "--no-apm-server-dashboards",
            action="store_false",
            dest="apm_server_dashboards",
            help="skip loading apm-server dashboards (setup.dashboards.enabled=false)",
        )
        parser.add_argument(
            '--apm-server-record',
            action="store_true",
            default=False,
            help=argparse.SUPPRESS,
            # help="record apm-server request payloads.",
        )
        parser.add_argument(
            '--apm-server-tee',
            action="store_true",
            default=False,
            help=argparse.SUPPRESS,
            # help="tee proxied traffic instead of load balancing.",
        )
        parser.add_argument(
            "--apm-server-opt",
            action="append",
            default=[],
            help="arbitrary additional configuration to set for apm-server"
        )
        parser.add_argument(
            "--apm-server-acm-disable",
            action="store_true",
            help="disable Agent Config Management",
        )

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
            if key not in self.bc["projects"][self.docker_name]["packages"]:
                key = "{image}-{version}-linux-amd64-docker-image.tar.gz".format(
                    image=image,
                    version=version,
                )
            return self.bc["projects"][self.docker_name]["packages"][key]
        except KeyError:
            # help debug manifest issues
            print(json.dumps(self.bc))
            raise

    def _content(self):
        command_args = []
        for param, value in self.apm_server_command_args:
            command_args.extend(["-E", param + "=" + value])

        healthcheck_path = "/" if self.at_least_version("6.5") else "/healthcheck"
        content = dict(
            cap_add=["CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"],
            cap_drop=["ALL"],
            command=["apm-server", "-e", "--httpprof", ":{}".format(self.apm_server_monitor_port)] + command_args,
            depends_on=self.depends_on,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, path=healthcheck_path),
            labels=["co.elastic.apm.stack-version=" + self.version],
            ports=[
                self.publish_port(self.port, self.SERVICE_PORT),
                self.publish_port(self.apm_server_monitor_port, self.DEFAULT_MONITOR_PORT),
            ]
        )

        if self.build:
            build_spec_parts = self.build.split("@", 1)
            repo = build_spec_parts[0]
            branch = build_spec_parts[1] if len(build_spec_parts) > 1 else "master"
            content.update({
                "build": {
                    "context": "docker/apm-server",
                    "args": {
                        "apm_server_base_image": self.default_image(),
                        "apm_server_branch_or_commit": branch,
                        "apm_server_repo": repo,
                    }
                },
                "image": None,
            })

        return content

    @staticmethod
    def enabled():
        return True

    def render(self):
        """hack up render to support multiple apm servers behind a load balancer"""
        ren = super(ApmServer, self).render()
        if self.apm_server_count == 1:
            return ren

        # save a single server for use as backend template
        single = ren[self.name()]
        single["ports"] = [p.rsplit(":", 1)[-1] for p in single["ports"]]

        # render proxy + backends
        if self.apm_server_tee:
            ren = self.render_tee()
        else:
            ren = self.render_proxy()

        # individualize each backend instance
        for i in range(1, self.apm_server_count + 1):
            backend = dict(single)
            backend["container_name"] = backend["container_name"] + "-" + str(i)
            if self.apm_server_tee and i > 1:
                backend["build"] = self.apm_server_tee_build
                backend["labels"] = ["co.elastic.apm.stack-version=8.0.0"]
                del(backend["image"])  # use the built one instead
            ren.update({"-".join([self.name(), str(i)]): backend})

        return ren

    def render_proxy(self):
        condition = {"condition": "service_healthy"}
        content = dict(
            build={"context": "docker/apm-server/haproxy"},
            container_name=self.default_container_name() + "-load-balancer",
            depends_on={"apm-server-{}".format(i): condition for i in range(1, self.apm_server_count + 1)},
            environment={"APM_SERVER_COUNT": self.apm_server_count},
            healthcheck={"test": ["CMD", "haproxy", "-c", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]},
            ports=[
                self.publish_port(self.port, self.SERVICE_PORT),
            ],
        )
        return {self.name(): content}

    def render_tee(self):
        condition = {"condition": "service_healthy"}
        command = ["teeproxy", "-l", "0.0.0.0:8200", "-a", "apm-server-1:8200", "-b", "apm-server-2:8200"]
        # add extra tee backends
        for i in range(3, self.apm_server_count + 1):
            command.extend(["-b", self.name() + "-" + str(i) + ":8200"])
        content = dict(
            build={"context": "docker/apm-server/teeproxy"},
            command=command,
            container_name=self.default_container_name() + "-tee",
            depends_on={"apm-server-{}".format(i): condition for i in range(1, self.apm_server_count + 1)},
            healthcheck={"test": ["CMD", "pgrep", "teeproxy"]},
            ports=[
                self.publish_port(self.port, self.SERVICE_PORT),
            ],
        )
        return {self.name(): content}


class Elasticsearch(StackService, Service):
    default_environment = [
        "bootstrap.memory_lock=true",
        "cluster.name=docker-cluster",
        "cluster.routing.allocation.disk.threshold_enabled=false",
        "discovery.type=single-node",
        "path.repo=/usr/share/elasticsearch/data/backups",
    ]
    default_heap_size = "1g"

    SERVICE_PORT = 9200

    def __init__(self, **options):
        super(Elasticsearch, self).__init__(**options)
        if not self.oss and not self.at_least_version("6.3"):
            self.docker_name = self.name() + "-platinum"

        self.xpack_secure = bool(self.options.get("xpack_secure"))

        # construct elasticsearch environment variables
        es_java_opts = {}
        if "elasticsearch_heap" in options:
            es_java_opts.update({
                "Xms": options["elasticsearch_heap"],
                "Xmx": options["elasticsearch_heap"],
            })
        es_java_opts.update(dict(options.get("elasticsearch_java_opts", {}) or {}))
        if self.at_least_version("6.4"):
            # per https://github.com/elastic/elasticsearch/pull/32138/files
            es_java_opts["XX:UseAVX"] = "=2"

        java_opts_env = "ES_JAVA_OPTS=" + " ".join(["-{}{}".format(k, v) for k, v in sorted(es_java_opts.items())])
        # falsy empty string permitted
        data_dir = self.version if options.get("elasticsearch_data_dir") is None else options["elasticsearch_data_dir"]

        self.environment = self.default_environment + [
            java_opts_env, "path.data=/usr/share/elasticsearch/data/" + data_dir]
        if not self.oss:
            xpack_security_enabled = "false"
            if self.xpack_secure:
                xpack_security_enabled = "true"
                if options.get("elasticsearch_xpack_audit"):
                    self.environment.append("xpack.security.audit.enabled=true")
                self.environment.append("xpack.security.authc.anonymous.roles=remote_monitoring_collector")
                if self.at_least_version("7.0"):
                    self.environment.append("xpack.security.authc.realms.file.file1.order=0")
                    self.environment.append("xpack.security.authc.realms.native.native1.order=1")
                else:
                    self.environment.append("xpack.security.authc.realms.file1.type=file")
                    self.environment.append("xpack.security.authc.realms.native1.type=native")
                    self.environment.append("xpack.security.authc.realms.native1.order=1")
            self.environment.append("xpack.security.enabled=" + xpack_security_enabled)
            self.environment.append("xpack.license.self_generated.type=trial")
            if self.at_least_version("6.3"):
                self.environment.append("xpack.monitoring.collection.enabled=true")

    @classmethod
    def add_arguments(cls, parser):
        super(Elasticsearch, cls).add_arguments(parser)
        parser.add_argument(
            "--elasticsearch-data-dir",
            help="override elasticsearch data dir.  Defaults to the current es version."
        )

        parser.add_argument(
            "--elasticsearch-heap",
            default=Elasticsearch.default_heap_size,
            help="min/max elasticsearch heap size, for -Xms -Xmx jvm options."
        )

        parser.add_argument(
            "--elasticsearch-xpack-audit",
            action="store_true",
            help="enable very verbose xpack auditing",
        )

        class storeDict(argparse.Action):
            def __call__(self, parser, namespace, value, option_string=None):
                items = getattr(namespace, self.dest)
                items.update(dict([value.split("=", 1)]))

        # this is a dict to enable deduplication
        # eg --elasticsearch-java-opts a==z --elasticsearch-java-opts a==b will add only -a=b to ES_JAVA_OPTS
        parser.add_argument(
            "--elasticsearch-java-opts",
            action=storeDict,
            default={},
            help="additional entries for ES_JAVA_OPTS, multiple allowed, separate key/value with =."
        )

    def _content(self):
        volumes = ["esdata:/usr/share/elasticsearch/data"]
        if self.xpack_secure:
            volumes.extend([
                "./docker/elasticsearch/roles.yml:/usr/share/elasticsearch/config/roles.yml",
                "./docker/elasticsearch/users:/usr/share/elasticsearch/config/users",
                "./docker/elasticsearch/users_roles:/usr/share/elasticsearch/config/users_roles",
            ])
        return dict(
            environment=self.environment,
            healthcheck={
                "interval": "20",
                "retries": 10,
                "test": ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -vq '\"status\":\"red\"'"],
            },
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
            ulimits={
                "memlock": {"hard": -1, "soft": -1},
            },
            volumes=volumes,
        )

    @staticmethod
    def enabled():
        return True


class BeatMixin(object):
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "logstash"}

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--{}-elasticsearch-url".format(cls.name()),
            action="append",
            dest="{}_elasticsearch_urls".format(cls.name()),
            help="{} elasticsearch output url(s).".format(cls.name())
        )
        parser.add_argument(
            "--{}-elasticsearch-username".format(cls.name()),
            help="{} elasticsearch output username.".format(cls.name()),
        )
        parser.add_argument(
            "--{}-elasticsearch-password".format(cls.name()),
            help="{} elasticsearch output password.".format(cls.name()),
        )
        parser.add_argument(
            "--{}-output".format(cls.name()),
            choices=cls.OUTPUTS,
            default="elasticsearch",
            help="{} output".format(cls.name()),
        )

    def __init__(self, **options):
        super(BeatMixin, self).__init__(**options)
        self.command = list(self.DEFAULT_COMMAND)
        self.depends_on = {"elasticsearch": {"condition": "service_healthy"}} if options.get(
            "enable_elasticsearch", True) else {}
        if options.get("enable_kibana", True):
            self.command.extend(["-E", "setup.dashboards.enabled=true"])
            self.depends_on["kibana"] = {"condition": "service_healthy"}
        self.environment = {}

        def add_es_config(args, prefix="output"):
            """add elasticsearch configuration options."""
            es_urls = options.get("{}_elasticsearch_urls".format(self.name())) or [self.DEFAULT_ELASTICSEARCH_HOSTS]
            default_beat_creds = {"username": "{}_user".format(self.name()), "password": "changeme"}
            args.append((prefix + ".elasticsearch.hosts", json.dumps(es_urls)))
            for cfg in ("username", "password"):
                es_opt = "{}_elasticsearch_{}".format(self.name(), cfg)
                if options.get(es_opt):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), options[es_opt]))
                elif options.get("xpack_secure"):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), default_beat_creds.get(cfg)))

        command_args = []
        add_es_config(command_args)
        beat_output = options.get("{}_output".format(self.name()), self.DEFAULT_OUTPUT)
        if beat_output == "elasticsearch":
            command_args.extend([("output.elasticsearch.enabled", "true")])
        else:
            command_args.extend([("output.elasticsearch.enabled", "false")])
            add_es_config(command_args, prefix="xpack.monitoring")
            if beat_output == "logstash":
                command_args.extend([
                    ("output.logstash.enabled", "true"),
                    ("output.logstash.hosts", "[\"logstash:5044\"]"),
                ])
            elif beat_output == "kafka":
                # disabled via command line options for now
                command_args.extend([
                    ("output.kafka.enabled", "true"),
                    ("output.kafka.hosts", "[\"kafka:9092\"]"),
                    ("output.kafka.topics", "[{default: '{}', topic: '{}'}]".format(self.name(), self.name())),
                ])

        for param, value in command_args:
            self.command.extend(["-E", param + "=" + value])

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
            if key not in self.bc["projects"]["beats"]["packages"]:
                # This is the old standard based on the format:
                # ${name}-${version}-${os}-${architecture}-${classifier}.${extension}
                key = "{image}-{version}-linux-amd64-docker-image.tar.gz".format(
                    image=image,
                    version=version,
                )
            return self.bc["projects"]["beats"]["packages"][key]
        except KeyError:
            try:
                # This is the new standard based on the format:
                # ${name}-${version}-${classifier}-${os}-${architecture}.${extension}
                key = "{image}-{version}-docker-image-linux-amd64.tar.gz".format(
                        image=image,
                        version=version,
                )
                return self.bc["projects"]["beats"]["packages"][key]
            except KeyError:
                # help debug manifest issues
                print(json.dumps(self.bc))
                raise


class Filebeat(BeatMixin, StackService, Service):
    DEFAULT_COMMAND = ["filebeat", "-e", "--strict.perms=false"]
    docker_path = "beats"

    def __init__(self, **options):
        super(Filebeat, self).__init__(**options)
        config = "filebeat.yml" if self.at_least_version("6.1") else "filebeat.simple.yml"
        self.filebeat_config_path = os.path.join(".", "docker", "filebeat", config)

    def _content(self):
        return dict(
            command=self.command,
            depends_on=self.depends_on,
            environment=self.environment,
            labels=None,
            user="root",
            volumes=[
                self.filebeat_config_path + ":/usr/share/filebeat/filebeat.yml",
                "/var/lib/docker/containers:/var/lib/docker/containers",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )


class Heartbeat(BeatMixin, StackService, Service):
    DEFAULT_COMMAND = ["heartbeat", "-e", "--strict.perms=false"]
    docker_path = "beats"

    def __init__(self, **options):
        options['enable_kibana'] = False
        super(Heartbeat, self).__init__(**options)
        config = "heartbeat.yml"
        self.heartbeat_config_path = os.path.join(".", "docker", "heartbeat", config)

    def _content(self):
        return dict(
            command=self.command,
            depends_on=self.depends_on,
            environment=self.environment,
            labels=None,
            user="root",
            volumes=[
                self.heartbeat_config_path + ":/usr/share/heartbeat/heartbeat.yml",
                "/var/lib/docker/containers:/var/lib/docker/containers",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )


class Kibana(StackService, Service):
    default_environment = {"SERVER_NAME": "kibana.example.org"}

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
            if options.get("xpack_secure"):
                self.environment["ELASTICSEARCH_PASSWORD"] = "changeme"
                self.environment["ELASTICSEARCH_USERNAME"] = "kibana_system_user"
                self.environment["STATUS_ALLOWANONYMOUS"] = "true"
        self.environment["ELASTICSEARCH_URL"] = ",".join(self.options.get(
            "kibana_elasticsearch_urls") or [self.DEFAULT_ELASTICSEARCH_HOSTS])

    @classmethod
    def add_arguments(cls, parser):
        super(Kibana, cls).add_arguments(parser)
        parser.add_argument(
            "--{}-elasticsearch-url".format(cls.name()),
            action="append",
            dest="kibana_elasticsearch_urls",
            help="kibana elasticsearch output url(s)."
        )

    def _content(self):
        return dict(
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "kibana", path="/api/status", retries=20),
            depends_on={"elasticsearch": {"condition": "service_healthy"}} if self.options.get(
                "enable_elasticsearch", True) else {},
            environment=self.environment,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )

    @staticmethod
    def enabled():
        return True


class Logstash(StackService, Service):
    SERVICE_PORT = 5044

    def build_candidate_manifest(self):
        version = self.version
        image = self.docker_name
        if self.oss:
            image += "-oss"
        key = "{image}-{version}-docker-image.tar.gz".format(
            image=image,
            version=version,
        )
        return self.bc["projects"]["logstash-docker"]["packages"][key]

    def _content(self):
        self.es_urls = ",".join(self.options.get(
            "logstash_elasticsearch_urls") or [self.DEFAULT_ELASTICSEARCH_HOSTS])
        return dict(
            depends_on={"elasticsearch": {"condition": "service_healthy"}} if self.options.get(
                "enable_elasticsearch", True) else {},
            environment={
                "ELASTICSEARCH_URL": self.es_urls,
                },
            healthcheck=curl_healthcheck(9600, "logstash", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT), "9600"],
            volumes=["./docker/logstash/pipeline/:/usr/share/logstash/pipeline/"]
        )

    @classmethod
    def add_arguments(cls, parser):
        super(Logstash, cls).add_arguments(parser)
        parser.add_argument(
            "--{}-elasticsearch-url".format(cls.name()),
            action="append",
            dest="logstash_elasticsearch_urls",
            help="logstash elasticsearch output url(s)."
        )


class Metricbeat(BeatMixin, StackService, Service):
    DEFAULT_COMMAND = ["metricbeat", "-e", "--strict.perms=false"]
    docker_path = "beats"

    @classmethod
    def add_arguments(cls, parser):
        super(Metricbeat, cls).add_arguments(parser)
        parser.add_argument(
            "--apm-server-pprof-url",
            help="apm server profiling url to use.",
            dest="apm_server_pprof_url",
            default="apm-server:6060"
        )

    def _content(self):
        self.environment['APM_SERVER_PPROF_HOST'] = self.options.get("apm_server_pprof_url")
        return dict(
            command=self.command,
            depends_on=self.depends_on,
            environment=self.environment,
            labels=None,
            user="root",
            volumes=[
                "./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml",
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )


class Packetbeat(BeatMixin, StackService, Service):
    """Stars a Packetbeat container to grab the network traffic."""

    DEFAULT_COMMAND = ["packetbeat", "-e", "--strict.perms=false", "-E", "packetbeat.interfaces.device=eth0"]
    docker_path = "beats"

    def _content(self):
        return dict(
            command=self.command,
            depends_on=self.depends_on,
            environment=self.environment,
            labels=None,
            user="root",
            privileged="true",
            cap_add=["NET_ADMIN", "NET_RAW"],
            network_mode="service:apm-server",
            volumes=[
                "./docker/packetbeat/packetbeat.yml:/usr/share/packetbeat/packetbeat.yml",
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
            image="confluentinc/cp-kafka:4.1.3",
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class Postgres(Service):
    SERVICE_PORT = 5432
    opbeans_side_car = True

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
    opbeans_side_car = True

    def _content(self):
        return dict(
            healthcheck={"interval": "10s", "test": ["CMD", "redis-cli", "ping"]},
            image="redis:4",
            labels=None,
            command="--save ''",  # disable persistence
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
class AgentRUMJS(Service):
    SERVICE_PORT = 8000
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-rum-js"

    def __init__(self, **options):
        super(AgentRUMJS, self).__init__(**options)
        self.agent_branch = options.get("rum_agent_branch", self.DEFAULT_AGENT_BRANCH)
        self.agent_repo = options.get("rum_agent_repo", self.DEFAULT_AGENT_REPO)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @classmethod
    def add_arguments(cls, parser):
        super(AgentRUMJS, cls).add_arguments(parser)
        parser.add_argument(
            '--rum-agent-repo',
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )
        parser.add_argument(
            '--rum-agent-branch',
            default=cls.DEFAULT_AGENT_BRANCH,
        )

    def _content(self):
        return dict(
            build=dict(
                context="docker/rum",
                dockerfile="Dockerfile",
                args=[
                    "RUM_AGENT_BRANCH=" + self.agent_branch,
                    "RUM_AGENT_REPO=" + self.agent_repo,
                    "APM_SERVER_URL=" + self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL)
                ]
            ),
            container_name="rum",
            image=None,
            labels=None,
            logging=None,
            environment={
                "ELASTIC_APM_SERVICE_NAME": "rum",
                "ELASTIC_APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL)
            },
            depends_on=self.depends_on,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "rum", path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentGoNetHttp(Service):
    SERVICE_PORT = 8080
    DEFAULT_AGENT_VERSION = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-go"

    @classmethod
    def add_arguments(cls, parser):
        super(AgentGoNetHttp, cls).add_arguments(parser)
        parser.add_argument(
            "--go-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
            help='Use Go agent version (master, 0.5, v0.5.2, ...)',
        )
        parser.add_argument(
            '--go-agent-repo',
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )

    def __init__(self, **options):
        super(AgentGoNetHttp, self).__init__(**options)
        self.agent_version = options.get("go_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_repo = options.get("go_agent_repo", self.DEFAULT_AGENT_REPO)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URL"),
    ])
    def _content(self):
        return dict(
            build={
                "context": "docker/go/nethttp",
                "dockerfile": "Dockerfile",
                "args": {
                    "GO_AGENT_BRANCH": self.agent_version,
                    "GO_AGENT_REPO": self.agent_repo,
                },
            },
            container_name="gonethttpapp",
            environment={
                "ELASTIC_APM_API_REQUEST_TIME": "3s",
                "ELASTIC_APM_FLUSH_INTERVAL": "500ms",
                "ELASTIC_APM_SERVICE_NAME": "gonethttpapp",
                "ELASTIC_APM_TRANSACTION_IGNORE_NAMES": "healthcheck",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "gonethttpapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentNodejsExpress(Service):
    # elastic/apm-agent-nodejs#master
    DEFAULT_AGENT_PACKAGE = "elastic-apm-node"
    SERVICE_PORT = 8010

    def __init__(self, **options):
        super(AgentNodejsExpress, self).__init__(**options)
        self.agent_package = options.get("nodejs_agent_package", self.DEFAULT_AGENT_PACKAGE)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @classmethod
    def add_arguments(cls, parser):
        super(AgentNodejsExpress, cls).add_arguments(parser)
        parser.add_argument(
            '--nodejs-agent-package',
            default=cls.DEFAULT_AGENT_PACKAGE,
            help='Use Node.js agent version (github;master, github;1.x, github;v3.0.0, release;latest, ...)',
        )

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URL"),
    ])
    def _content(self):
        return dict(
            build={"context": "docker/nodejs/express", "dockerfile": "Dockerfile"},
            command="bash -c \"npm install {} && node app.js\"".format(
                self.agent_package, self.SERVICE_PORT),
            container_name="expressapp",
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "expressapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            environment={
                "EXPRESS_PORT": str(self.SERVICE_PORT),
                "EXPRESS_SERVICE_NAME": "expressapp",
            },
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentPython(Service):
    DEFAULT_AGENT_PACKAGE = "elastic-apm"
    _agent_python_arguments_added = False

    def __init__(self, **options):
        super(AgentPython, self).__init__(**options)
        self.agent_package = options.get("python_agent_package", self.DEFAULT_AGENT_PACKAGE)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @classmethod
    def add_arguments(cls, parser):
        if cls._agent_python_arguments_added:
            return

        super(AgentPython, cls).add_arguments(parser)
        parser.add_argument(
            '--python-agent-package',
            default=cls.DEFAULT_AGENT_PACKAGE,
            help='Use Python agent version (github;master, github;1.x, github;v3.0.0, release;latest, ...)',
        )
        # prevent calling again
        cls._agent_python_arguments_added = True

    def _content(self):
        raise NotImplementedError()


class AgentPythonDjango(AgentPython):
    SERVICE_PORT = 8003

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "APM_SERVER_URL"),
    ])
    def _content(self):
        return dict(
            build={"context": "docker/python/django", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -q -U {} && python testapp/manage.py runserver 0.0.0.0:{}\"".format(
                self.agent_package, self.SERVICE_PORT),
            container_name="djangoapp",
            environment={
                "DJANGO_PORT": self.SERVICE_PORT,
                "DJANGO_SERVICE_NAME": "djangoapp",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "djangoapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentPythonFlask(AgentPython):
    SERVICE_PORT = 8001

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "APM_SERVER_URL"),
    ])
    def _content(self):
        return dict(
            build={"context": "docker/python/flask", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -q -U {} && gunicorn app:app\"".format(self.agent_package),
            container_name="flaskapp",
            image=None,
            labels=None,
            logging=None,
            environment={
                "FLASK_SERVICE_NAME": "flaskapp",
                "GUNICORN_CMD_ARGS": "-w 4 -b 0.0.0.0:{}".format(self.SERVICE_PORT),
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "flaskapp"),
            depends_on=self.depends_on,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentRubyRails(Service):
    DEFAULT_AGENT_REPO = "elastic/apm-agent-ruby"
    DEFAULT_AGENT_VERSION = "latest"
    DEFAULT_AGENT_VERSION_STATE = "release"
    SERVICE_PORT = 8020

    @classmethod
    def add_arguments(cls, parser):
        super(AgentRubyRails, cls).add_arguments(parser)
        parser.add_argument(
            "--ruby-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
            help='Use Ruby agent version (master, 1.x, latest, ...)',
        )
        parser.add_argument(
            "--ruby-agent-version-state",
            default=cls.DEFAULT_AGENT_VERSION_STATE,
            help='Use Ruby agent version state (github or release)',
        )
        parser.add_argument(
            "--ruby-agent-repo",
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )

    def __init__(self, **options):
        super(AgentRubyRails, self).__init__(**options)
        self.agent_version = options.get("ruby_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_version_state = options.get("ruby_agent_version_state", self.DEFAULT_AGENT_VERSION_STATE)
        self.agent_repo = options.get("ruby_agent_repo", self.DEFAULT_AGENT_REPO)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
    ])
    def _content(self):
        return dict(
            build={
                "context": "docker/ruby/rails",
                "dockerfile": "Dockerfile",
                "args": {
                    "RUBY_AGENT_VERSION": self.agent_version,
                    "RUBY_AGENT_REPO": self.agent_repo,
                }
            },
            command="bash -c \"bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p {}\"".format(
                self.SERVICE_PORT),
            container_name="railsapp",
            environment={
                "APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
                "ELASTIC_APM_API_REQUEST_TIME": "3s",
                "ELASTIC_APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
                "ELASTIC_APM_SERVICE_NAME": "railsapp",
                "RAILS_PORT": self.SERVICE_PORT,
                "RAILS_SERVICE_NAME": "railsapp",
                "RUBY_AGENT_VERSION_STATE": self.agent_version_state,
                "RUBY_AGENT_VERSION": self.agent_version,
                "RUBY_AGENT_REPO": self.agent_repo,
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "railsapp", retries=60),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentJavaSpring(Service):
    SERVICE_PORT = 8090
    DEFAULT_AGENT_VERSION = "master"
    DEFAULT_AGENT_RELEASE = ""
    DEFAULT_AGENT_REPO = "elastic/apm-agent-java"

    @classmethod
    def add_arguments(cls, parser):
        super(AgentJavaSpring, cls).add_arguments(parser)
        parser.add_argument(
            "--java-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
            help='Use Java agent version (master, 0.5, v.0.7.1, ...)',
        )
        parser.add_argument(
            "--java-agent-release",
            default=cls.DEFAULT_AGENT_RELEASE,
            help='Use Java agent release version (1.6.0, 0.6.2, ...)',
        )
        parser.add_argument(
            "--java-agent-repo",
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )

    def __init__(self, **options):
        super(AgentJavaSpring, self).__init__(**options)
        self.agent_version = options.get("java_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_release = options.get("java_agent_release", self.DEFAULT_AGENT_RELEASE)
        self.agent_repo = options.get("java_agent_repo", self.DEFAULT_AGENT_REPO)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URL"),
    ])
    def _content(self):
        return dict(
            build={
                "context": "docker/java/spring",
                "dockerfile": "Dockerfile",
                "args": {
                    "JAVA_AGENT_BRANCH": self.agent_version,
                    "JAVA_AGENT_BUILT_VERSION": self.agent_release,
                    "JAVA_AGENT_REPO": self.agent_repo,
                }
            },
            container_name="javaspring",
            image=None,
            labels=None,
            logging=None,
            environment={
                "ELASTIC_APM_API_REQUEST_TIME": "3s",
                "ELASTIC_APM_SERVICE_NAME": "springapp",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "javaspring"),
            depends_on=self.depends_on,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentDotnet(Service):
    SERVICE_PORT = 8100
    DEFAULT_AGENT_VERSION = "master"
    DEFAULT_AGENT_RELEASE = ""
    DEFAULT_AGENT_REPO = "elastic/apm-agent-dotnet"

    @classmethod
    def add_arguments(cls, parser):
        super(AgentDotnet, cls).add_arguments(parser)
        parser.add_argument(
            "--dotnet-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
            help='Use .NET agent version (master, 0.0.0.2, 0.0.0.1, ...)',
        )
        parser.add_argument(
            "--dotnet-agent-release",
            default=cls.DEFAULT_AGENT_RELEASE,
            help='Use .NET agent release version (0.0.1-alpha, 0.0.2-alpha, ...)',
        )
        parser.add_argument(
            "--dotnet-agent-repo",
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )

    def __init__(self, **options):
        super(AgentDotnet, self).__init__(**options)
        self.agent_version = options.get("dotnet_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_release = options.get("dotnet_agent_release", self.DEFAULT_AGENT_RELEASE)
        self.agent_repo = options.get("dotnet_agent_repo", self.DEFAULT_AGENT_REPO)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URLS"),
    ])
    def _content(self):
        return dict(
            build={
                "context": "docker/dotnet",
                "dockerfile": "Dockerfile",
                "args": {
                    "DOTNET_AGENT_BRANCH": self.agent_version,
                    "DOTNET_AGENT_VERSION": self.agent_release,
                    "DOTNET_AGENT_REPO": self.agent_repo,
                },
            },
            container_name="dotnetapp",
            environment={
                "ELASTIC_APM_API_REQUEST_TIME": "3s",
                "ELASTIC_APM_FLUSH_INTERVAL": "5",
                "ELASTIC_APM_SAMPLE_RATE": "1",
                "ELASTIC_APM_SERVICE_NAME": "dotnetapp",
                "ELASTIC_APM_TRANSACTION_IGNORE_NAMES": "healthcheck",
            },
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "dotnetapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


#
# Opbeans Services
#


class OpbeansService(Service):
    def __init__(self, **options):
        super(OpbeansService, self).__init__(**options)
        self.apm_server_url = options.get("apm_server_url", DEFAULT_APM_SERVER_URL)
        self.apm_js_server_url = options.get("opbeans_apm_js_server_url", DEFAULT_APM_JS_SERVER_URL)
        self.opbeans_dt_probability = options.get("opbeans_dt_probability", 0.5)
        if hasattr(self, "DEFAULT_SERVICE_NAME"):
            self.service_name = options.get(self.option_name() + "_service_name", self.DEFAULT_SERVICE_NAME)
        self.agent_branch = options.get(self.option_name() + "_agent_branch") or ""
        self.agent_repo = options.get(self.option_name() + "_agent_repo") or ""
        self.agent_local_repo = options.get(self.option_name() + "_agent_local_repo")
        self.opbeans_branch = options.get(self.option_name() + "_branch") or ""
        self.opbeans_repo = options.get(self.option_name() + "_repo") or ""
        self.es_urls = ",".join(self.options.get("opbeans_elasticsearch_urls") or [self.DEFAULT_ELASTICSEARCH_HOSTS])
        self.service_environment = \
            options.get(self.option_name() + "_service_environment") or self.DEFAULT_ELASTIC_APM_ENVIRONMENT

    @classmethod
    def add_arguments(cls, parser):
        """add service-specific command line arguments"""
        # allow port overrides
        super(OpbeansService, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-agent-branch',
            default=None,
            dest=cls.option_name() + '_agent_branch',
            help=cls.name() + " branch for agent"
        )
        parser.add_argument(
            '--' + cls.name() + '-agent-repo',
            default=None,
            dest=cls.option_name() + '_agent_repo',
            help=cls.name() + " github repo for agent (in form org/repo)"
        )
        parser.add_argument(
            '--' + cls.name() + '-agent-local-repo',
            default=None,
            dest=cls.option_name() + '_agent_local_repo',
            help=cls.name() + " local repo path for agent"
        )
        parser.add_argument(
            '--' + cls.name() + '-service-environment',
            default=None,
            dest=cls.option_name() + '_service_environment',
            help=cls.name() + " service.environment value to display."
        )
        if hasattr(cls, 'DEFAULT_SERVICE_NAME'):
            parser.add_argument(
                '--' + cls.name() + '-service-name',
                default=cls.DEFAULT_SERVICE_NAME,
                dest=cls.option_name() + '_service_name',
                help=cls.name() + " service name"
            )


class OpbeansDotnet(OpbeansService):
    SERVICE_PORT = 3004
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-dotnet"
    DEFAULT_SERVICE_NAME = "opbeans-dotnet"
    DEFAULT_AGENT_VERSION = ""
    DEFAULT_OPBEANS_BRANCH = "master"
    DEFAULT_OPBEANS_REPO = "elastic/opbeans-dotnet"
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansDotnet, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-version',
            default=cls.DEFAULT_AGENT_VERSION,
        )
        parser.add_argument(
            '--' + cls.name() + '-branch',
            default=cls.DEFAULT_OPBEANS_BRANCH,
            dest=cls.option_name() + '_branch',
            help=cls.name() + " branch for the opbeans dotnet"
        )
        parser.add_argument(
            '--' + cls.name() + '-repo',
            default=cls.DEFAULT_OPBEANS_REPO,
            dest=cls.option_name() + '_repo',
            help=cls.name() + " github repo for the opbeans dotnet (in form org/repo)"
        )

    def __init__(self, **options):
        super(OpbeansDotnet, self).__init__(**options)
        self.agent_version = options.get('opbeans_dotnet_version')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {}
        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}
        if self.options.get("enable_elasticsearch", True):
            depends_on["elasticsearch"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/dotnet",
                dockerfile="Dockerfile",
                args=[
                    "DOTNET_AGENT_BRANCH=" + (self.agent_branch or self.DEFAULT_AGENT_BRANCH),
                    "DOTNET_AGENT_REPO=" + (self.agent_repo or self.DEFAULT_AGENT_REPO),
                    "DOTNET_AGENT_VERSION=" + (self.agent_version or self.DEFAULT_AGENT_VERSION),
                    "OPBEANS_DOTNET_BRANCH=" + (self.opbeans_branch or self.DEFAULT_OPBEANS_BRANCH),
                    "OPBEANS_DOTNET_REPO=" + (self.opbeans_repo or self.DEFAULT_OPBEANS_REPO),
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_SERVER_URLS={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_SAMPLE_RATE=1",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(80, "opbeans-dotnet", path="/", retries=36),
            ports=[self.publish_port(self.port, 80)],
        )
        return content


class OpbeansDotnet01(OpbeansDotnet):
    SERVICE_PORT = 3104
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansDotnet01, self).__init__(**options)


class OpbeansGo(OpbeansService):
    SERVICE_PORT = 3003
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-go"
    DEFAULT_OPBEANS_BRANCH = "master"
    DEFAULT_OPBEANS_REPO = "elastic/opbeans-go"
    DEFAULT_SERVICE_NAME = "opbeans-go"
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansGo, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-branch',
            default=cls.DEFAULT_OPBEANS_BRANCH,
            dest=cls.option_name() + '_branch',
            help=cls.name() + " branch for the opbeans go"
        )
        parser.add_argument(
            '--' + cls.name() + '-repo',
            default=cls.DEFAULT_OPBEANS_REPO,
            dest=cls.option_name() + '_repo',
            help=cls.name() + " github repo for the opbeans go (in form org/repo)"
        )

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}
        if self.options.get("enable_elasticsearch", True):
            depends_on["elasticsearch"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/go",
                dockerfile="Dockerfile",
                args=[
                    "GO_AGENT_BRANCH=" + (self.agent_branch or self.DEFAULT_AGENT_BRANCH),
                    "GO_AGENT_REPO=" + (self.agent_repo or self.DEFAULT_AGENT_REPO),
                    "OPBEANS_GO_BRANCH=" + (self.opbeans_branch or self.DEFAULT_OPBEANS_BRANCH),
                    "OPBEANS_GO_REPO=" + (self.opbeans_repo or self.DEFAULT_OPBEANS_REPO),
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_SAMPLE_RATE=1",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_CACHE=redis://redis:6379",
                "OPBEANS_PORT=3000",
                "PGHOST=postgres",
                "PGPORT=5432",
                "PGUSER=postgres",
                "PGPASSWORD=verysecure",
                "PGSSLMODE=disable",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            ports=[self.publish_port(self.port, 3000)],
        )
        return content


class OpbeansGo01(OpbeansGo):
    SERVICE_PORT = 3103
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansGo01, self).__init__(**options)


class OpbeansJava(OpbeansService):
    SERVICE_PORT = 3002
    DEFAULT_AGENT_BRANCH = ""
    DEFAULT_AGENT_REPO = "elastic/apm-agent-java"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = 'opbeans-java'
    DEFAULT_OPBEANS_IMAGE = 'opbeans/opbeans-java'
    DEFAULT_OPBEANS_VERSION = 'latest'
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansJava, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-image',
            default=cls.DEFAULT_OPBEANS_IMAGE,
            help=cls.name() + " image for the opbeans java"
        )
        parser.add_argument(
            '--' + cls.name() + '-version',
            default=cls.DEFAULT_OPBEANS_VERSION,
            help=cls.name() + " version for the docker image of opbeans java"
        )

    def __init__(self, **options):
        super(OpbeansJava, self).__init__(**options)
        self.opbeans_image = options.get('opbeans_java_image')
        self.opbeans_version = options.get('opbeans_java_version')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
        }

        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}
        if self.options.get("enable_elasticsearch", True):
            depends_on["elasticsearch"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/java",
                dockerfile="Dockerfile",
                args=[
                    "JAVA_AGENT_BRANCH=" + (self.agent_branch or self.DEFAULT_AGENT_BRANCH),
                    "JAVA_AGENT_REPO=" + (self.agent_repo or self.DEFAULT_AGENT_REPO),
                    "OPBEANS_JAVA_IMAGE=" + (self.opbeans_image or self.DEFAULT_OPBEANS_IMAGE),
                    "OPBEANS_JAVA_VERSION=" + (self.opbeans_version or self.DEFAULT_OPBEANS_VERSION),
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
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_SERVER_PORT=3000",
                "JAVA_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(3000, "opbeans-java", path="/", retries=36),
            ports=[self.publish_port(self.port, 3000)],
        )
        if self.agent_local_repo:
            content["volumes"] = [
                "{}:/local-install".format(self.agent_local_repo),
            ]
        return content


class OpbeansJava01(OpbeansJava):
    SERVICE_PORT = 3102
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansJava01, self).__init__(**options)


class OpbeansNode(OpbeansService):
    SERVICE_PORT = 3000
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_OPBEANS_IMAGE = 'opbeans/opbeans-node'
    DEFAULT_OPBEANS_VERSION = 'latest'
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansNode, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-image',
            default=cls.DEFAULT_OPBEANS_IMAGE,
            help=cls.name() + " image for the opbeans node"
        )
        parser.add_argument(
            '--' + cls.name() + '-version',
            default=cls.DEFAULT_OPBEANS_VERSION,
            help=cls.name() + " version for the docker image of opbeans node"
        )

    def __init__(self, **options):
        super(OpbeansNode, self).__init__(**options)
        self.service_name = "opbeans-node"
        self.opbeans_image = options.get('opbeans_node_image')
        self.opbeans_version = options.get('opbeans_node_version')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/node",
                dockerfile="Dockerfile",
                args=[
                    "OPBEANS_NODE_IMAGE=" + (self.opbeans_image or self.DEFAULT_OPBEANS_IMAGE),
                    "OPBEANS_NODE_VERSION=" + (self.opbeans_version or self.DEFAULT_OPBEANS_VERSION),
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_LOG_LEVEL=info",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "WORKLOAD_ELASTIC_APM_APP_NAME=workload",
                "WORKLOAD_ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "WORKLOAD_DISABLED={}".format(self.options.get("no_opbeans_node_loadgen", False)),
                "OPBEANS_SERVER_PORT=3000",
                "OPBEANS_SERVER_HOSTNAME=opbeans-node",
                "NODE_ENV=production",
                "PGHOST=postgres",
                "PGPASSWORD=verysecure",
                "PGPORT=5432",
                "PGUSER=postgres",
                "REDIS_URL=redis://redis:6379",
                "NODE_AGENT_BRANCH=" + self.agent_branch,
                "NODE_AGENT_REPO=" + self.agent_repo,
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(3000, "opbeans-node", path="/"),
            ports=[self.publish_port(self.port, 3000)],
            volumes=[
                "./docker/opbeans/node/sourcemaps:/sourcemaps",
            ]
        )
        if self.agent_local_repo:
            content["volumes"].append(
                "{}:/local-install".format(self.agent_local_repo),
            )
        return content


class OpbeansNode01(OpbeansNode):
    SERVICE_PORT = 3100
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansNode01, self).__init__(**options)


class OpbeansPython(OpbeansService):
    SERVICE_PORT = 8000
    DEFAULT_AGENT_REPO = "elastic/apm-agent-python"
    DEFAULT_AGENT_BRANCH = "2.x"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = 'opbeans-python'
    DEFAULT_OPBEANS_IMAGE = 'opbeans/opbeans-python'
    DEFAULT_OPBEANS_VERSION = 'latest'
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansPython, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-local-repo',
            default=cls.DEFAULT_LOCAL_REPO,
        )
        parser.add_argument(
            '--' + cls.name() + '-image',
            default=cls.DEFAULT_OPBEANS_IMAGE,
            help=cls.name() + " image for the opbeans python"
        )
        parser.add_argument(
            '--' + cls.name() + '-version',
            default=cls.DEFAULT_OPBEANS_VERSION,
            help=cls.name() + " version for the docker image of opbeans python"
        )

    def __init__(self, **options):
        super(OpbeansPython, self).__init__(**options)
        self.opbeans_image = options.get('opbeans_python_image')
        self.opbeans_version = options.get('opbeans_python_version')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}
        if self.options.get("enable_elasticsearch", True):
            depends_on["elasticsearch"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/python",
                dockerfile="Dockerfile",
                args=[
                    "OPBEANS_PYTHON_IMAGE=" + (self.opbeans_image or self.DEFAULT_OPBEANS_IMAGE),
                    "OPBEANS_PYTHON_VERSION=" + (self.opbeans_version or self.DEFAULT_OPBEANS_VERSION),
                ]
            ),
            environment=[
                "DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans",
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_SERVER_URL=http://opbeans-python:3000",
                "PYTHON_AGENT_BRANCH=" + self.agent_branch,
                "PYTHON_AGENT_REPO=" + self.agent_repo,
                "PYTHON_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(3000, "opbeans-python", path="/"),
            ports=[self.publish_port(self.port, 3000)],
        )
        if self.agent_local_repo:
            content["volumes"] = [
                "{}:/local-install".format(self.agent_local_repo),
            ]
        return content


class OpbeansPython01(OpbeansPython):
    SERVICE_PORT = 8100
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansPython01, self).__init__(**options)


class OpbeansRuby(OpbeansService):
    SERVICE_PORT = 3001
    DEFAULT_AGENT_BRANCH = "master"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-ruby"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = "opbeans-ruby"
    DEFAULT_OPBEANS_IMAGE = 'opbeans/opbeans-ruby'
    DEFAULT_OPBEANS_VERSION = 'latest'
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansRuby, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-image',
            default=cls.DEFAULT_OPBEANS_IMAGE,
            help=cls.name() + " image for the opbeans ruby"
        )
        parser.add_argument(
            '--' + cls.name() + '-version',
            default=cls.DEFAULT_OPBEANS_VERSION,
            help=cls.name() + " version for the docker image of opbeans ruby"
        )

    def __init__(self, **options):
        super(OpbeansRuby, self).__init__(**options)
        self.opbeans_image = options.get('opbeans_ruby_image')
        self.opbeans_version = options.get('opbeans_ruby_version')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    def _content(self):
        depends_on = {
            "postgres": {"condition": "service_healthy"},
            "redis": {"condition": "service_healthy"},
        }

        if self.options.get("enable_apm_server", True):
            depends_on["apm-server"] = {"condition": "service_healthy"}
        if self.options.get("enable_elasticsearch", True):
            depends_on["elasticsearch"] = {"condition": "service_healthy"}

        content = dict(
            build=dict(
                context="docker/opbeans/ruby",
                dockerfile="Dockerfile",
                args=[
                    "OPBEANS_RUBY_IMAGE=" + (self.opbeans_image or self.DEFAULT_OPBEANS_IMAGE),
                    "OPBEANS_RUBY_VERSION=" + (self.opbeans_version or self.DEFAULT_OPBEANS_VERSION),
                ]
            ),
            environment=[
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_SERVICE_NAME={}".format(self.service_name),
                "DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_SERVER_URL=http://opbeans-ruby:3000",
                "RAILS_ENV=production",
                "RAILS_LOG_TO_STDOUT=1",
                "PORT=3000",
                "RUBY_AGENT_BRANCH=" + self.agent_branch,
                "RUBY_AGENT_REPO=" + self.agent_repo,
                "RUBY_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            # lots of retries as the ruby app can take a long time to boot
            healthcheck=curl_healthcheck(3000, "opbeans-ruby", path="/", retries=50),
            ports=[self.publish_port(self.port, 3000)],
        )
        if self.agent_local_repo:
            content["volumes"] = [
                "{}:/local-install".format(self.agent_local_repo),
            ]
        return content


class OpbeansRuby01(OpbeansRuby):
    SERVICE_PORT = 3101
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansRuby01, self).__init__(**options)


class OpbeansRum(Service):
    # OpbeansRum is not really an Opbeans service, so we inherit from Service
    SERVICE_PORT = 9222

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansRum, cls).add_arguments(parser)
        parser.add_argument(
            '--' + cls.name() + '-backend-service',
            default='opbeans-node',
        )
        parser.add_argument(
            '--' + cls.name() + '-backend-port',
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
            healthcheck=curl_healthcheck(self.SERVICE_PORT, path="/"),
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
        return content


class OpbeansLoadGenerator(Service):
    opbeans_side_car = True

    @classmethod
    def add_arguments(cls, parser):
        super(OpbeansLoadGenerator, cls).add_arguments(parser)
        for service_class in OpbeansService.__subclasses__():
            parser.add_argument(
                '--no-%s-loadgen' % service_class.name(),
                action='store_true',
                default=False,
                help='Disable load generator for {}'.format(service_class.name())
            )
            parser.add_argument(
                '--%s-loadgen-rpm' % service_class.name(),
                action='store',
                default=100,
                help='RPM of load that should be generated for {}'.format(service_class.name())
            )

    def __init__(self, **options):
        super(OpbeansLoadGenerator, self).__init__(**options)
        self.loadgen_services = []
        self.loadgen_rpms = OrderedDict()
        # create load for opbeans services
        run_all_opbeans = options.get('run_all_opbeans') or options.get('run_all')
        excluded = ('opbeans_load_generator', 'opbeans_rum', 'opbeans_node', 'opbeans_node', 'opbeans_dotnet01',
                    'opbeans_go01', 'opbeans_java01', 'opbeans_node01', 'opbeans_python01', 'opbeans_ruby01')
        for flag, value in options.items():
            if (value or run_all_opbeans) and flag.startswith('enable_opbeans_'):
                service_name = flag[len('enable_'):]
                if not options.get('no_{}_loadgen'.format(service_name)) and service_name not in excluded:
                    self.loadgen_services.append(service_name.replace('_', '-'))
                    rpm = options.get('{}_loadgen_rpm'.format(service_name))
                    if rpm:
                        self.loadgen_rpms[service_name.replace('_', '-')] = rpm

    def _content(self):
        content = dict(
            image="opbeans/opbeans-loadgen:latest",
            depends_on={service: {'condition': 'service_healthy'} for service in self.loadgen_services},
            environment=[
                "OPBEANS_URLS={}".format(','.join('{0}:http://{0}:3000'.format(s) for s in sorted(self.loadgen_services))),  # noqa: E501
                "OPBEANS_RPMS={}".format(','.join('{}:{}'.format(k, v) for k, v in sorted(self.loadgen_rpms.items())))
            ],
            labels=None,
        )
        return content


#
# Service Tests
#

class LocalSetup(object):
    SUPPORTED_VERSIONS = {
        '6.0': '6.0.1',
        '6.1': '6.1.4',
        '6.2': '6.2.4',
        '6.3': '6.3.2',
        '6.4': '6.4.3',
        '6.5': '6.5.4',
        '6.6': '6.6.2',
        '6.7': '6.7.2',
        '6.8': '6.8.3',
        '7.0': '7.0.1',
        '7.1': '7.1.1',
        '7.2': '7.2.1',
        '7.3': '7.3.1',
        '7.4': '7.4.0',
        'master': '8.0.0',
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

        # Add a --no-x / --with-x argument for each service
        for service in services:
            if not service.opbeans_side_car:
                enabled_group = parser.add_mutually_exclusive_group()
                enabled_group.add_argument(
                    '--with-' + service.name(),
                    action='store_true',
                    dest='enable_' + service.option_name(),
                    help='Enable ' + service.name(),
                    default=service.enabled(),
                )

                enabled_group.add_argument(
                    '--no-' + service.name(),
                    action='store_false',
                    dest='enable_' + service.option_name(),
                    help='Disable ' + service.name(),
                    default=service.enabled(),
                )
            service.add_arguments(parser)

        parser.add_argument(
            '--opbeans-dt-probability',
            action="store",
            type=float,
            default=0.5,
            help="Set probability of Opbeans Distributed Ping Pong. 0 disables it."
        )

        # Add build candidate argument
        build_type_group = parser.add_mutually_exclusive_group()
        build_type_group.add_argument(
            '--bc',
            const="latest",
            nargs="?",
            help=(
                'ID of the build candidate, e.g. 37b864a0. '
                "override default 'latest' by providing an argument."
            ),
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
            "--build-parallel",
            action="store_true",
            help="build images in parallel",
            dest="build_parallel",
            default=False,
        )

        parser.add_argument(
            '--force-build',
            action='store_true',
            help='force build of any images without docker cache',
            dest='force_build',
            default=False,
        )

        parser.add_argument(
            '--skip-pull',
            action='store_true',
            help='skip pulling a newer version of the image',
            dest='skip_pull',
            default=False,
        )

        parser.add_argument(
            '--remove-orphans',
            action='store_true',
            help='remove services that no longer exist',
            dest='remove_orphans',
            default=False,
        )

        parser.add_argument(
            '--all',
            action='store_true',
            help='run all services',
            dest='run_all',
            default=False,
        )

        parser.add_argument(
            '--all-opbeans',
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
            "--apm-server-url",
            action="store",
            help="apm server url to use for all clients",
            default=DEFAULT_APM_SERVER_URL,
        )

        parser.add_argument(
            '--opbeans-apm-js-server-url',
            action='store',
            help='server_url to use for Opbeans frontend service',
            dest='opbeans_apm_js_server_url',
            default='http://apm-server:8200',
        )

        parser.add_argument(
            "--opbeans-elasticsearch-url",
            action="append",
            dest="opbeans_elasticsearch_urls",
            help="opbeans elasticsearch output url(s)."
        )

        parser.add_argument(
            '--with-services',
            action="append",
            default=[],
            help="merge additional service definitions into the final docker-compose configuration",
        )

        parser.add_argument(
            '--xpack-secure',
            action="store_true",
            dest="xpack_secure",
            help="enable xpack security throughout the stack",
        )

        self.store_options(parser)

        return parser

    def run_docker_compose_process(self, docker_compose_cmd):
        try:
            subprocess.call(docker_compose_cmd)
        except OSError as err:
            print('ERROR: Docker Compose might be missing. See below for further details.\n')
            raise OSError(err)

    @staticmethod
    def init_sourcemap_parser(parser):
        parser.add_argument(
            "--apm-server-url",
            action="store",
            help="server_url to use for Opbeans services",
            default=DEFAULT_APM_SERVER_URL,
        )

        parser.add_argument(
            "--opbeans-frontend-sourcemap",
            help="path to the sourcemap. Defaults to first map found in docker/opbeans/node/sourcemaps directory",
        )

        parser.add_argument(
            "--opbeans-frontend-service-name",
            default="client",
            help='Name of the frontend app. Defaults to "opbeans-react"',
        )

        parser.add_argument(
            "--opbeans-frontend-service-version",
            default="1.0.0",
            help='Version of the frontend app. Defaults to the BUILDDATE env variable of the "opbeans-node" container',
        )

        parser.add_argument(
            "--opbeans-frontend-bundle-path",
            help='Bundle path in minified files. Defaults to "http://opbeans-node:3000/static/js/" + name of sourcemap',
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
                '-f \'{{ index .Config.Labels "co.elastic.apm.stack-version" }}\''
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
                'docker-compose run --rm --no-ansi --log-level ERROR' +
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
        run_all = args.get("run_all")
        all_opbeans = args.get('run_all_opbeans') or run_all
        any_opbeans = all_opbeans or any(v and k.startswith('enable_opbeans_') for k, v in args.items())
        for service in self.services:
            service_enabled = args.get("enable_" + service.option_name())
            is_opbeans_service = issubclass(service, OpbeansService) or service is OpbeansRum
            is_opbeans_sidecar = service.name() in ('postgres', 'redis', 'opbeans-load-generator')
            is_opbeans_2nd = service.name() in ('opbeans-go01', 'opbeans-java01',
                                                'opbeans-python01', 'opbeans-ruby01',
                                                'opbeans-dotnet01', 'opbeans-node01')
            is_obs = issubclass(service, BeatMixin)
            if service_enabled or (all_opbeans and is_opbeans_service and not is_opbeans_2nd) \
                    or (any_opbeans and is_opbeans_sidecar and not is_opbeans_2nd) or \
                    (run_all and is_obs and not is_opbeans_2nd):
                selections.add(service(**args))

        # `docker load` images if necessary, usually only for build candidates
        services_to_load = {}
        for service in selections:
            download_url = service.image_download_url()
            if download_url:
                services_to_load[service.name()] = download_url
        if not args["skip_download"] and services_to_load:
            load_images(set(services_to_load.values()), args["image_cache_dir"])

        # generate docker-compose.yml
        services = {}
        for service in selections:
            services.update(service.render())

        for addl_services in args['with_services']:
            with open(addl_services) as f:
                services.update(json.load(f))

        # expose a list of enabled opbeans services to all opbeans services. This allows them to talk amongst each other
        # and have a jolly good distributed time
        enabled_opbeans_services = [k for k in services.keys()
                                    if k.startswith("opbeans-") and k not in ("opbeans-rum", "opbeans-load-generator")]
        enabled_opbeans_services_str = ",".join(enabled_opbeans_services)
        for s in enabled_opbeans_services:
            if isinstance(services[s]["environment"], dict):
                services[s]["environment"]["OPBEANS_SERVICES"] = enabled_opbeans_services_str
            else:
                services[s]["environment"].append("OPBEANS_SERVICES=" + enabled_opbeans_services_str)

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
            docker_compose_cmd = ["docker-compose", "-f", docker_compose_path.name]
            if not sys.stdin.isatty():
                docker_compose_cmd.extend(["--no-ansi", "--log-level", "ERROR"])

            # always build if possible, should be quick for rebuilds
            build_services = [name for name, service in compose["services"].items() if 'build' in service]
            if build_services:
                docker_compose_build = docker_compose_cmd + ["build"]
                if not args["skip_pull"]:
                    docker_compose_build.append("--pull")
                if args["force_build"]:
                    docker_compose_build.append("--no-cache")
                if args["build_parallel"]:
                    docker_compose_build.append("--parallel")
                self.run_docker_compose_process(docker_compose_build + build_services)

            # pull any images
            image_services = [name for name, service in compose["services"].items() if
                              'image' in service and name not in services_to_load]
            if image_services and not args["skip_download"]:
                pull_params = ["pull"]
                if not sys.stdin.isatty():
                    pull_params.extend(["-q"])
                self.run_docker_compose_process(docker_compose_cmd + pull_params + image_services)

            # really start
            up_params = ["up", "-d"]
            if args["remove_orphans"]:
                up_params.append("--remove-orphans")
            if not sys.stdin.isatty():
                up_params.extend(["--quiet-pull"])
            self.run_docker_compose_process(docker_compose_cmd + up_params)

    @staticmethod
    def status_handler():
        print("Status for all services:\n")
        subprocess.call(['docker-compose', 'ps'])

    @staticmethod
    def stop_handler():
        print("Stopping all stack services..\n")
        subprocess.call(['docker-compose', "--no-ansi", "--log-level", "ERROR", 'stop'])

    def upload_sourcemaps_handler(self):
        service_name = self.args.opbeans_frontend_service_name
        sourcemap_file = self.args.opbeans_frontend_sourcemap
        bundle_path = self.args.opbeans_frontend_bundle_path
        service_version = self.args.opbeans_frontend_service_version

        if sourcemap_file:
            sourcemap_file = os.path.expanduser(sourcemap_file)
            if not os.path.exists(sourcemap_file):
                print('{} not found. Try again :)'.format(sourcemap_file))
                sys.exit(1)
        else:
            try:
                g = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docker/opbeans/node/sourcemaps/*.map'))
                sourcemap_file = glob.glob(g)[0]
            except IndexError:
                print(
                    'No source map found in {} '.format(g) +
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
        print("Uploading {} for {} version {}".format(sourcemap_file, service_name, service_version))
        cmd = (
            'curl -sS -X POST '
            '-F service_name="{service_name}" '
            '-F service_version="{service_version}" '
            '-F bundle_filepath="{bundle_path}" '
            '-F sourcemap=@/tmp/sourcemap '
            '{auth_header}'
            '{server_url}/v1/client-side/sourcemaps'
        ).format(
            service_name=service_name,
            service_version=service_version,
            bundle_path=bundle_path,
            sourcemap_file=sourcemap_file,
            auth_header=auth_header,
            server_url=self.args.apm_server_url,
        )
        cmd = "docker run --rm --network apm-integration-testing " + \
              "-v {}:/tmp/sourcemap centos:7 ".format(sourcemap_file) + cmd
        subprocess.check_output(cmd, shell=True).decode('utf8').strip()

    @staticmethod
    def versions_handler():
        Container = collections.namedtuple(
            'Container', ('service', 'stack_version', 'created')
        )
        cmd = (
            'docker ps --filter "name=localtesting" -q | xargs docker inspect '
            '-f \'{{ index .Config.Labels "co.elastic.apm.stack-version" }}\\t{{ .Image }}\\t{{ .Name }}\''
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


def main():
    # Enable logging
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s')
    setup = LocalSetup(sys.argv[1:])
    setup()


if __name__ == '__main__':
    main()
