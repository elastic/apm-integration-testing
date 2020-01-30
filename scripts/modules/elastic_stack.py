#
# Elastic Services
#

import argparse
import json
import os

from .helpers import curl_healthcheck
from .service import StackService, Service


class ApmServer(StackService, Service):
    docker_path = "apm"

    SERVICE_PORT = "8200"
    DEFAULT_MONITOR_PORT = "6060"
    DEFAULT_JAEGER_HTTP_PORT = "14268"
    DEFAULT_JAEGER_GRPC_PORT = "14250"
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "file", "kafka", "logstash"}
    DEFAULT_KIBANA_HOST = "kibana:5601"

    def __init__(self, **options):
        super(ApmServer, self).__init__(**options)
        default_apm_server_creds = {"username": "apm_server_user", "password": "changeme"}

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
            ("setup.template.settings.index.number_of_replicas", "0"),
            ("setup.template.settings.index.number_of_shards", "1"),
            ("setup.template.settings.index.refresh_interval",
                "{}".format(self.options.get("apm_server_index_refresh_interval"))),
            ("monitoring.elasticsearch" if self.at_least_version("7.2") else "xpack.monitoring.elasticsearch", "true"),
            ("monitoring.enabled" if self.at_least_version("7.2") else "xpack.monitoring.enabled", "true")
        ])
        if options.get("apm_server_self_instrument", True):
            self.apm_server_command_args.append(("apm-server.instrumentation.enabled", "true"))
            if self.at_least_version("7.6") and options.get("apm_server_profile", True):
                self.apm_server_command_args.extend([
                    ("apm-server.instrumentation.profiling.cpu.enabled", "true"),
                    ("apm-server.instrumentation.profiling.heap.enabled", "true"),
                ])
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
                ("apm-server.kibana.host",
                    self.options.get("apm_server_kibana_url", ""))])
            agent_config_poll = self.options.get("agent_config_poll", "30s")
            self.apm_server_command_args.append(("apm-server.agent.config.cache.expiration", agent_config_poll))
            if self.options.get("xpack_secure"):
                for cfg in ("username", "password"):
                    es_opt = "apm_server_elasticsearch_{}".format(cfg)
                    if self.options.get(es_opt):
                        self.apm_server_command_args.append(("apm-server.kibana.{}".format(cfg), self.options[es_opt]))
                    elif self.options.get("xpack_secure"):
                        self.apm_server_command_args.append(
                            ("apm-server.kibana.{}".format(cfg), default_apm_server_creds.get(cfg)))

        if self.options.get("enable_kibana", True):
            self.depends_on["kibana"] = {"condition": "service_healthy"}
            if options.get("apm_server_dashboards", True) and not self.at_least_version("7.0") \
                    and not self.options.get("xpack_secure"):
                self.apm_server_command_args.append(
                    ("setup.dashboards.enabled", "true")
                )

        if self.at_least_version("7.6"):
            if options.get("apm_server_jaeger"):
                self.apm_server_command_args.extend([
                    ("apm-server.jaeger.http.enabled", "true"),
                    ("apm-server.jaeger.http.host", "0.0.0.0:" + self.DEFAULT_JAEGER_HTTP_PORT),
                    ("apm-server.jaeger.grpc.enabled", "true"),
                    ("apm-server.jaeger.grpc.host", "0.0.0.0:" + self.DEFAULT_JAEGER_GRPC_PORT)
                ])

        # configure authentication
        if options.get("apm_server_api_key_auth", False):
            self.apm_server_command_args.append(("apm-server.api_key.enabled", "true"))
        if self.options.get("apm_server_secret_token"):
            self.apm_server_command_args.append(("apm-server.secret_token", self.options["apm_server_secret_token"]))

        if self.options.get("apm_server_enable_tls"):
            self.apm_server_command_args.extend([
                ("apm-server.ssl.enabled", "true"),
                ("apm-server.ssl.key", "/usr/share/apm-server/config/certs/tls.key"),
                ("apm-server.ssl.certificate", "/usr/share/apm-server/config/certs/tls.crt")
            ])

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
                if options.get("apm_server_pipeline_path"):
                    self.apm_server_command_args.append(
                        ("apm-server.register.ingest.pipeline.overwrite", "true"),
                    )
        else:
            add_es_config(self.apm_server_command_args,
                          prefix="monitoring" if self.at_least_version("7.2") else "xpack.monitoring")
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
            "--apm-server-pipeline-path",
            help='custom apm-server pipeline definition.'
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
            "--no-apm-server-profile",
            action="store_false",
            help='disable apm-server self instrumentation profiling.'
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
            "--apm-server-api-key-auth",
            action="store_true",
            help="enable apm-server api key authentication for agent communication.",
        )
        parser.add_argument(
            '--apm-server-secret-token',
            dest="apm_server_secret_token",
            help="apm-server secret token.",
        )
        parser.add_argument(
            '--no-apm-server-jaeger',
            dest="apm_server_jaeger",
            action="store_false",
            help="make apm-server act as a Jaeger collector (HTTP and gRPC).",
        )
        parser.add_argument(
            '--apm-server-enable-tls',
            action="store_true",
            dest="apm_server_enable_tls",
            help="apm-server enable TLS with pre-configured selfsigned certificates.",
        )
        parser.add_argument(
            '--apm-server-agent-config-poll',
            default="30s",
            dest="agent_config_poll",
            help="agent config polling interval.",
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
        parser.add_argument(
            "--apm-server-kibana-url",
            default=cls.DEFAULT_KIBANA_HOST,
            help="Change the default kibana URL (kibana:5601)"
        )
        parser.add_argument(
            "--apm-server-index-refresh-interval",
            default="1ms",
            help="change the index refresh interval (default 1ms)",
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

        ports = [
            self.publish_port(self.port, self.SERVICE_PORT),
            self.publish_port(self.apm_server_monitor_port, self.DEFAULT_MONITOR_PORT),
        ]
        if ("apm-server.jaeger.http.enabled", "true") in self.apm_server_command_args:
            ports.append(self.publish_port(self.DEFAULT_JAEGER_HTTP_PORT))

        if ("apm-server.jaeger.grpc.enabled", "true") in self.apm_server_command_args:
            ports.append(self.publish_port(self.DEFAULT_JAEGER_GRPC_PORT))

        content = dict(
            cap_add=["CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"],
            cap_drop=["ALL"],
            command=["apm-server", "-e", "--httpprof", ":{}".format(self.apm_server_monitor_port)] + command_args,
            depends_on=self.depends_on,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, path=healthcheck_path),
            labels=["co.elastic.apm.stack-version=" + self.version],
            ports=ports
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

        volumes = []
        if self.options.get("apm_server_enable_tls"):
            volumes.extend([
                "./scripts/tls/cert.crt:/usr/share/apm-server/config/certs/tls.crt",
                "./scripts/tls/key.pem:/usr/share/apm-server/config/certs/tls.key"
            ])

            content.update({
                "healthcheck": {
                    "interval": "10s",
                    "retries": 12,
                    "test": [
                        "CMD",
                        "curl",
                        "--write-out",
                        "'HTTP %{http_code}'",
                        "--fail",
                        "--silent",
                        "--output",
                        "/dev/null",
                        "-k",
                        "https://localhost:8200/"
                    ]
                },
            })

        overwrite_pipeline_path = self.options.get("apm_server_pipeline_path")
        if overwrite_pipeline_path:
            volumes.extend([
                "{}:/usr/share/apm-server/ingest/pipeline/definition.json".format(overwrite_pipeline_path)])

        if volumes:
            content["volumes"] = volumes

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
        if self.at_least_version("8.0"):
            self.environment.append("indices.id_field_data.enabled=true")
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
                if self.at_least_version("7.3"):
                    self.environment.append("xpack.security.authc.token.enabled=true")
                    self.environment.append("xpack.security.authc.api_key.enabled=true")
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
                if self.at_least_version("7.6"):
                    self.environment["XPACK_SECURITY_LOGINASSISTANCEMESSAGE"] = (
                        "Login&#32;details:&#32;`{}/{}`.&#32;Further&#32;details&#32;[here]({}).").format(
                        self.environment["ELASTICSEARCH_USERNAME"], self.environment["ELASTICSEARCH_PASSWORD"],
                        "https://github.com/elastic/apm-integration-testing#logging-in")
            if self.at_least_version("7.6"):
                if not options.get("no_kibana_apm_servicemaps"):
                    self.environment["XPACK_APM_SERVICEMAPENABLED"] = "true"
        urls = self.options.get("kibana_elasticsearch_urls") or [self.DEFAULT_ELASTICSEARCH_HOSTS]
        self.environment["ELASTICSEARCH_URL"] = ",".join(urls)

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--kibana-elasticsearch-url",
            action="append",
            dest="kibana_elasticsearch_urls",
            help="kibana elasticsearch output url(s)."
        )

        parser.add_argument(
            "--no-kibana-apm-servicemaps",
            action="store_true",
            help="disable the APM service maps UI",
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
