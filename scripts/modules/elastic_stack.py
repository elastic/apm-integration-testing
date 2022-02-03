#
# Elastic Services
#

import argparse
import json
import os
import platform

from .helpers import curl_healthcheck, try_to_set_slowlog, urlparse
from .service import StackService, Service, DEFAULT_APM_SERVER_URL


class ApmServer(StackService, Service):
    docker_path = "apm"

    SERVICE_PORT = "8200"
    DEFAULT_MONITOR_PORT = "6060"
    DEFAULT_JAEGER_HTTP_PORT = "14268"
    DEFAULT_JAEGER_GRPC_PORT = "14250"
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "file", "kafka", "logstash"}
    DEFAULT_KIBANA_HOST = "kibana:5601"
    STACK_CA_PATH = "/usr/share/apm-server/config/certs/stack-ca.crt"

    def __init__(self, **options):
        super(ApmServer, self).__init__(**options)

        default_apm_server_es_creds = {"username": "apm_server_user", "password": "changeme"}
        default_apm_server_kibana_creds = dict(default_apm_server_es_creds)
        self.managed = False

        # run apm-server managed by elastic-agent
        if self.options.get("apm_server_managed"):
            if self.version_lower_than("7.11"):
                raise Exception("APM Server managed by Elastic Agent is only available in 7.11+")
            self.managed = True
            self.apm_server_command_args = []

            kibana_url = options.get("elastic_agent_kibana_url")
            if not kibana_url:
                kibana_scheme = "https" if self.options.get("kibana_enable_tls", False) else "http"
                kibana_url = kibana_scheme + "://admin:changeme@" + self.DEFAULT_KIBANA_HOST
            self.depends_on = {"kibana": {"condition": "service_healthy"},
                               "elastic-agent": {"condition": "service_healthy"}}

            self.managed_environment = {"KIBANA_HOST": kibana_url,
                                        "APM_SERVER_SECRET_TOKEN": self.options.get("apm_server_secret_token", "")}

            if self.at_least_version("7.13"):
                self.managed_environment["FLEET_SERVER_ENABLE"] = "1"

            url = package_registry_url(options)
            if url:
                self.managed_environment["XPACK_FLEET_REGISTRYURL"] = url

            # Not yet supported when run under elastic-agent:
            # - apm-server config options
            # - teeproxy and haproxy not yet supported
            self.apm_server_count = 1
            return

        # run apm-server standalone
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
            ("monitoring.enabled" if self.at_least_version("7.2") else "xpack.monitoring.enabled", "true"),
            ("apm-server.rum.allow_headers", "[\"x-custom-header\"]")
        ])

        self.enable_data_streams = bool(self.options.get("apm_server_enable_data_streams"))
        if self.enable_data_streams:
            self.apm_server_command_args.append(("apm-server.data_streams.enabled", "true"))
            default_apm_server_kibana_creds = {"username": "admin", "password": "changeme"}

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

        self.es_tls = self.options.get("elasticsearch_enable_tls", False)
        self.kibana_tls = self.options.get("kibana_enable_tls", False)

        if self.options.get("apm_server_experimental_mode", True) and self.at_least_version("7.2"):
            self.apm_server_command_args.append(("apm-server.mode", "experimental"))

        index_suffix = self.options.get("index_suffix")
        if index_suffix and self.at_least_version("7.9"):
            mapping = []
            for et in ["profile", "error", "transaction", "span", "metric"]:
                mapping.append({"event_type": et, "index_suffix": index_suffix})
            mapping_str = json.dumps(mapping)
            self.apm_server_command_args.append(("apm-server.ilm.setup.mapping", mapping_str))

        if self.options.get("apm_server_ilm_disable"):
            self.apm_server_command_args.append(("apm-server.ilm.enabled", "false"))
        elif self.at_least_version("7.2") and not self.at_least_version("7.3") and not self.oss:
            self.apm_server_command_args.append(("apm-server.ilm.enabled", "true"))

        if self.options.get("apm_server_acm_disable") or not self.options.get("enable_kibana", True):
            self.apm_server_command_args.append(("apm-server.kibana.enabled", "false"))
        elif self.at_least_version("7.3") and self.options.get("enable_kibana", True):
            self.apm_server_command_args.extend([
                ("apm-server.kibana.enabled", "true"),
                ("apm-server.kibana.host", self.options.get("apm_server_kibana_url", self.DEFAULT_KIBANA_HOST))])
            if self.kibana_tls:
                self.apm_server_command_args.extend([
                    ("apm-server.kibana.protocol", "https"),
                    ("apm-server.kibana.ssl.certificate_authorities", '["' + self.STACK_CA_PATH + '"]'),
                ])

            agent_config_poll = self.options.get("agent_config_poll", "30s")
            self.apm_server_command_args.append(("apm-server.agent.config.cache.expiration", agent_config_poll))
            if self.options.get("xpack_secure"):
                for cfg in ("username", "password"):
                    es_opt = "apm_server_elasticsearch_{}".format(cfg)
                    if self.options.get(es_opt):
                        self.apm_server_command_args.append(("apm-server.kibana.{}".format(cfg), self.options[es_opt]))
                    elif self.options.get("xpack_secure"):
                        self.apm_server_command_args.append(
                            ("apm-server.kibana.{}".format(cfg), default_apm_server_kibana_creds.get(cfg)))

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

        if options.get('drop_unsampled') or (options.get('drop_unsampled') is None and self.at_least_version("7.16")):
            self.apm_server_command_args.extend([
                ("apm-server.sampling.keep_unsampled", "true")
            ])

        es_urls = []

        def add_es_config(args, prefix="output", tls=self.es_tls):
            """add elasticsearch configuration options."""
            args.append((prefix + ".elasticsearch.hosts", json.dumps(es_urls)))
            for cfg in ("username", "password"):
                es_opt = "apm_server_elasticsearch_{}".format(cfg)
                if self.options.get(es_opt):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), self.options[es_opt]))
                elif self.options.get("xpack_secure"):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), default_apm_server_es_creds.get(cfg)))
            if tls:
                args.append((prefix + ".elasticsearch.ssl.certificate_authorities", "['" + self.STACK_CA_PATH + "']"))

        es_urls = self.options.get("apm_server_elasticsearch_urls") or [self.default_elasticsearch_hosts(self.es_tls)]

        if self.apm_server_output == "elasticsearch":
            add_es_config(self.apm_server_command_args)
            self.apm_server_command_args.extend([
                ("output.elasticsearch.enabled", "true"),
            ])
            # pipeline is defined in the data stream settings, don't set a pipeline in that case, no overrides
            if options.get("apm_server_enable_pipeline", True) and self.at_least_version("6.5") and \
                    not self.enable_data_streams:
                if self.at_least_version("7.2"):
                    pipeline_name = "apm"
                else:
                    pipeline_name = "apm_user_agent"

                self.apm_server_command_args.append(
                    ("output.elasticsearch.pipelines", "[{pipeline: '%s'}]" % pipeline_name)
                )

                self.apm_server_command_args.extend([
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
                        "apm_server_branch": "main",
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
            "--no-apm-server-ilm",
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
            "--apm-server-enable-data-streams",
            action="store_true",
            help='enable writing to data streams'
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
            "--no-apm-server-acm",
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
        parser.add_argument(
            '--elastic-apm-api-key',
            dest='elastic_apm_api_key',
            help='API Key to authenticate against the APM server.'
        )
        parser.add_argument(
            '--apm-server-enable-debug',
            action="store_true",
            dest="apm_server_enable_debug",
            default=False,
            help="apm-server enable all the debugging output.",
        )
        parser.add_argument(
            '--apm-server-managed',
            action="store_true",
            dest="apm_server_managed",
            default=False,
            help="run apm-server managed by elastic-agent",
        )

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
        if self.managed:
            return dict()

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

        command = ["apm-server", "-e", "--httpprof", ":{}".format(self.apm_server_monitor_port)] + command_args
        if self.options.get("apm_server_enable_debug"):
            command = command + ["-d", "*"]

        content = dict(
            cap_add=["CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"],
            cap_drop=["ALL"],
            command=command,
            depends_on=self.depends_on,
            environment=[
                "BEAT_STRICT_PERMS=false"  # Workaround https://github.com/elastic/beats/issues/18858
            ],
            healthcheck=curl_healthcheck(self.SERVICE_PORT, path=healthcheck_path),
            labels=["co.elastic.apm.stack-version=" + self.version],
            ports=ports
        )

        if self.build:
            build_spec_parts = self.build.split("@", 1)
            repo = build_spec_parts[0]
            branch = build_spec_parts[1] if len(build_spec_parts) > 1 else "main"
            binary = "apm-server-oss" if self.oss else "apm-server"
            content.update({
                "build": {
                    "context": "docker/apm-server",
                    "args": {
                        "apm_server_base_image": self.default_image(),
                        "apm_server_branch_or_commit": branch,
                        "apm_server_repo": repo,
                        "apm_server_binary": binary,
                    }
                },
                "image": None,
            })

        volumes = []
        # don't unconditionally add this ca so quick start can be depenedency free
        if self.es_tls or self.kibana_tls:
            volumes.extend([
                "./scripts/tls/ca/ca.crt:" + self.STACK_CA_PATH,
            ])
        if self.options.get("apm_server_enable_tls"):
            volumes.extend([
                "./scripts/tls/apm-server/cert.crt:/usr/share/apm-server/config/certs/tls.crt",
                "./scripts/tls/apm-server/key.pem:/usr/share/apm-server/config/certs/tls.key"
            ])

            content.update({
                "healthcheck": curl_healthcheck(self.SERVICE_PORT, path="/", interval="10s", retries=12, https=True)
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
        """hack up render to support multiple apm servers behind a load balancer and apm-server under elastic agent"""
        ren = super(ApmServer, self).render()
        if self.apm_server_count == 1:
            if self.managed:
                # run a managed server
                ren = self.render_managed()
                return ren
            else:
                # return starndard apm-server
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

    def render_managed(self):
        content = dict(
            build={"context": "docker/apm-server/managed"},
            container_name=self.default_container_name() + "-managed",
            depends_on=self.depends_on,
            environment=self.managed_environment,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, host="elastic-agent", path="/", interval="10s", retries=12)
        )
        return {self.name(): content}

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


class PackageRegistry(StackService, Service):
    SERVICE_PORT = "8080"

    docker_path = "package-registry"
    docker_name = "distribution"

    def __init__(self, **options):
        super(PackageRegistry, self).__init__(**options)
        if not self.at_least_version("7.10"):
            raise Exception("Package registry only supported for 7.10+")
        self.distribution = options.get("package_registry_distribution", "snapshot")
        self.apm_package = options.get("package_registry_apm_path")
        self.environment = {}

    def _content(self):
        content = dict(
            image="/".join((self.docker_registry, self.docker_path, self.docker_name)) + ":" + self.distribution,
            environment=self.environment,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, path="/", interval="5s", retries=10),
            ports=[self.publish_port(self.SERVICE_PORT)]
        )
        if self.apm_package:
            content["volumes"] = [self.apm_package + ":/packages/" + self.distribution + "/apm"]
        return content

    @classmethod
    def add_arguments(cls, parser):
        super(PackageRegistry, cls).add_arguments(parser)
        parser.add_argument(
            "--package-registry-distribution",
            default="snapshot",
            choices=['snapshot', 'staging', 'production'],
            help="Package registry distribution"
        )
        parser.add_argument(
            "--package-registry-apm-path",
            help="Folder of a local APM package to add to the registry"
        )


class ElasticAgent(StackService, Service):
    docker_path = "beats"

    def __init__(self, **options):
        super(ElasticAgent, self).__init__(**options)
        if not self.at_least_version("7.8"):
            raise Exception("Elastic Agent is only available in 7.8+")

        # build deps
        self.depends_on = {"kibana": {"condition": "service_healthy"}} if options.get("enable_kibana", True) else {}

        # build environment
        #
        # Environment variables consumed by the Elastic Agent entrypoint
        # ---- Preparing Kibana for Fleet
        # KIBANA_FLEET_SETUP - set to 1 enables this setup

        # ---- Bootstrapping Fleet Server
        # This bootstraps the Fleet Server to be run by this Elastic Agent.
        # At least one Fleet Server is required in a Fleet deployment for
        # other Elastic Agent to bootstrap.

        # FLEET_SERVER_ENABLE - set to 1 enables bootstrapping of
        # Fleet Server (forces FLEET_ENROLL enabled)
        # FLEET_SERVER_POLICY_NAME - name of policy for the Fleet Server to use for itself

        # ---- Elastic Agent Fleet Enrollment
        # This enrolls the Elastic Agent into a Fleet Server. It is also possible
        # to have this create a new enrollment token for this specific Elastic Agent.
        # FLEET_ENROLL - set to 1 for enrollment to occur
        # FLEET_INSECURE - communicate with Fleet with either insecure HTTP or un-verified HTTPS

        # --------------
        kibana_url = options.get("elastic_agent_kibana_url")
        if not kibana_url:
            kibana_scheme = "https" if self.options.get("kibana_enable_tls", False) else "http"
            # TODO(gr): add default elastic-agent user
            kibana_url = kibana_scheme + "://admin:changeme@" + self.DEFAULT_KIBANA_HOST
        kibana_parsed_url = urlparse(kibana_url)

        es_url = options.get("elastic_agent_elasticsearch_url")
        if not es_url:
            es_scheme = "https" if self.options.get("elasticsearch_enable_tls", False) else "http"
            es_url = es_scheme + "://admin:changeme@" + self.DEFAULT_ELASTICSEARCH_HOST
        es_parsed_url = urlparse(es_url)

        self.environment = {
            "KIBANA_FLEET_SETUP": "1",
            "FLEET_SERVER_ENABLE": "1",
            "FLEET_ENROLL": "1",
            "FLEET_SERVER_INSECURE_HTTP": "1",
            "KIBANA_HOST": kibana_url,
            "ELASTICSEARCH_HOST": es_url,
            "FLEET_SERVER_HOST": "0.0.0.0"
        }
        if self.version_lower_than("7.13"):
            self.environment["FLEET_SETUP"] = "1"
        if kibana_parsed_url.password:
            self.environment["KIBANA_PASSWORD"] = kibana_parsed_url.password
        if kibana_parsed_url.username:
            self.environment["KIBANA_USERNAME"] = kibana_parsed_url.username
        if not kibana_url.startswith("https://"):
            self.environment["FLEET_INSECURE"] = "1"
            if self.version_lower_than("7.13"):
                self.environment["FLEET_ENROLL_INSECURE"] = 1
        if es_parsed_url.password:
            self.environment["ELASTICSEARCH_PASSWORD"] = es_parsed_url.password
        if es_parsed_url.username:
            self.environment["ELASTICSEARCH_USERNAME"] = es_parsed_url.username

        # set ports for defined integrations
        self.ports = [self.publish_port("8220")]
        if self.options.get("enable_apm_server") and self.options.get("apm_server_managed"):
            self.ports.append(self.publish_port(self.options.get(
                "apm_server_port", ApmServer.SERVICE_PORT), ApmServer.SERVICE_PORT))

    def _content(self):
        return dict(
            depends_on=self.depends_on,
            environment=self.environment,
            healthcheck={
                "test": ["CMD", "/bin/true"],
            },
            ports=self.ports,
            volumes=[
                "/var/run/docker.sock:/var/run/docker.sock",
            ]
        )

    @classmethod
    def add_arguments(cls, parser):
        super(ElasticAgent, cls).add_arguments(parser)
        parser.add_argument(
            "--elastic-agent-kibana-url",
            default="http://admin:changeme@" + cls.DEFAULT_KIBANA_HOST,
            help="Elastic Agent's Kibana URL, including username:password"
        )
        parser.add_argument(
            "--elastic-agent-elasticsearch-url",
            default="http://admin:changeme@" + cls.DEFAULT_ELASTICSEARCH_HOST,
            help="Elastic Agent's Elasticsearch URL, including username:password"
        )

    def build_candidate_manifest(self):
        version = self.version
        image = self.docker_name
        if self.oss:
            image += "-oss"
        if self.ubi8:
            image += "-ubi8"

        key = "{image}-{version}-docker-image-linux-amd64.tar.gz".format(
            image=image,
            version=version,
        )
        try:
            return self.bc["projects"]["beats"]["packages"][key]
        except KeyError:
            # help debug manifest issues
            print(json.dumps(self.bc))
            raise


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
        # AVX aren't valid instructions on ARM architectures. From Java 11 onwards this
        # flag isn't needed. We should most likely remove the if clause after 8.x.
        arm_architectures = ['aarch64', 'arm64']
        if self.at_least_version("6.4") and not platform.machine() in arm_architectures:
            # per https://github.com/elastic/elasticsearch/pull/32138/files
            es_java_opts["XX:UseAVX"] = "=2"

        java_opts_env = "ES_JAVA_OPTS=" + " ".join(["-{}{}".format(k, v) for k, v in sorted(es_java_opts.items())])
        # falsy empty string permitted
        data_dir = self.version if options.get("elasticsearch_data_dir") is None else options["elasticsearch_data_dir"]

        self.environment = self.default_environment + [
            java_opts_env, "path.data=/usr/share/elasticsearch/data/" + data_dir]
        snapshot_urls = [s for s in self.options.get("elasticsearch_snapshot_repo", []) if s.startswith("http")]
        if snapshot_urls:
            self.environment.append("repositories.url.allowed_urls={:s}".format(",".join(snapshot_urls)))
        self.es_tls = not self.oss and self.options.get("elasticsearch_enable_tls", False)
        if options.get("elasticsearch_slow_log"):
            try_to_set_slowlog(options.get("apm_server_elasticsearch_password"))
        if self.at_least_version("8.0"):
            self.environment.append("indices.id_field_data.enabled=true")
            self.environment.append("action.destructive_requires_name=false")
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
            if self.es_tls:
                certs = "/usr/share/elasticsearch/config/certs/tls.crt"
                certsKey = "/usr/share/elasticsearch/config/certs/tls.key"
                caCerts = "/usr/share/elasticsearch/config/certs/ca.crt"
                self.environment.append("xpack.security.http.ssl.enabled=true")
                self.environment.append("xpack.security.transport.ssl.enabled=true")
                self.environment.append("xpack.security.http.ssl.key=" + certsKey)
                self.environment.append("xpack.security.http.ssl.certificate=" + certs)
                self.environment.append("xpack.security.http.ssl.certificate_authorities=" + caCerts)
                self.environment.append("xpack.security.transport.ssl.key=" + certsKey)
                self.environment.append("xpack.security.transport.ssl.certificate=" + certs)
                self.environment.append("xpack.security.transport.ssl.certificate_authorities=" + caCerts)

    @classmethod
    def add_arguments(cls, parser):
        super(Elasticsearch, cls).add_arguments(parser)
        parser.add_argument(
            "--elasticsearch-data-dir",
            help="override elasticsearch data dir.  Defaults to the current es version."
        )

        parser.add_argument(
            '--elasticsearch-enable-tls',
            action="store_true",
            dest="elasticsearch_enable_tls",
            help="elasticsearch enable TLS with pre-configured selfsigned certificates.",
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

        parser.add_argument(
            "--elasticsearch-slow-log",
            action="store_true",
            help="enable the Elasticsearch slow log"
        )

        parser.add_argument(
            "--elasticsearch-snapshot-repo",
            action="append",
            default=[],
            help="configure elasticsearch snapshot repository",
        )

        class storeDict(argparse.Action):
            def __call__(self, parser, namespace, value, option_string=None):
                items = getattr(namespace, self.dest)
                if '=' in value:
                    items.update({value.lstrip('-'): ''})
                else:
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
        protocol = 'https' if self.es_tls else 'http'

        labels = self.default_labels()
        if self.at_least_version("6.3"):
            labels.extend([
                "co.elastic.metrics/module=elasticsearch",
                "co.elastic.metrics/metricsets=node,node_stats",
                "co.elastic.metrics/hosts={}://$${{data.host}}:9200".format(protocol),
            ])
            if self.es_tls:
                labels.extend([
                    "co.elastic.metrics/ssl.enabled=true",
                    "co.elastic.metrics/ssl.verification_mode=none",
                ])

        volumes = ["esdata:/usr/share/elasticsearch/data"]
        if self.xpack_secure:
            volumes.extend([
                "./docker/elasticsearch/roles.yml:/usr/share/elasticsearch/config/roles.yml",
                "./docker/elasticsearch/users:/usr/share/elasticsearch/config/users",
                "./docker/elasticsearch/users_roles:/usr/share/elasticsearch/config/users_roles",
            ])
        if self.es_tls:
            volumes.extend([
                "./scripts/tls/elasticsearch/elasticsearch.crt:/usr/share/elasticsearch/config/certs/tls.crt",
                "./scripts/tls/elasticsearch/elasticsearch.key:/usr/share/elasticsearch/config/certs/tls.key",
                "./scripts/tls/ca/ca.crt:/usr/share/elasticsearch/config/certs/ca.crt"
            ])

        entrypoint = "{}://localhost:9200/_cluster/health".format(protocol)
        return dict(
            environment=self.environment,
            healthcheck={
                "interval": "20s",
                "retries": 10,
                "test": ["CMD-SHELL", "curl -s -k {} | grep -vq '\"status\":\"red\"'".format(entrypoint)]
            },
            labels=labels,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
            ulimits={
                "memlock": {"hard": -1, "soft": -1},
            },
            volumes=volumes,
        )

    @staticmethod
    def enabled():
        return True


class EnterpriseSearch(StackService, Service):
    SERVICE_PORT = 3002
    EXTERNAL_PORT = 3005

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
            "--{}-password".format(cls.name()),
            default="changeme",
            help="{} user password.".format(cls.name()),
        )
        parser.add_argument(
            "--{}-port".format(cls.name()),
            default=cls.EXTERNAL_PORT,
            help="Enterprise search exposed port.",
        )

    def __init__(self, **options):
        super(EnterpriseSearch, self).__init__(**options)
        self.depends_on = {"elasticsearch": {"condition": "service_healthy"}} if options.get(
            "enable_elasticsearch", True) else {}

        self.environment = {
            "allow_es_settings_modification": "true",
            "ent_search.external_url": "http://localhost:{}".format(self.port),
            "secret_management.encryption_keys": '[4a2cd3f81d39bf28738c10db0ca782095ffac07279561809eecc722e0c20eb09]',
            "apm.enabled": "true",
            "apm.server_url": options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
            "ELASTIC_APM_ACTIVE": "true",
            "ELASTIC_APM_SERVER_URL": options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
            "ENT_SEARCH_DEFAULT_PASSWORD": options.get("enterprise_search_password", "changeme")
        }

        self.es_tls = options.get("elasticsearch_enable_tls", False)
        self.kibana_tls = options.get("kibana_enable_tls", False)
        es_urls = self.options.get("enterprise_search_elasticsearch_urls") or \
            [self.default_elasticsearch_hosts(self.es_tls)]
        self.environment["elasticsearch.host"] = es_urls[0]
        kibana_scheme = "https" if self.kibana_tls else "http"
        self.environment.update({
            "kibana.external_url": kibana_scheme + "://localhost:5601",
            "kibana.host": kibana_scheme + "://kibana:5601",
        })

        default_creds = {"username": "admin", "password": "changeme"}
        for cfg in ("username", "password"):
            es_opt = "{}_elasticsearch_{}".format(self.name(), cfg)
            if options.get(es_opt):
                self.environment.update({"elasticsearch.{}".format(cfg): options[es_opt]})
            elif options.get("xpack_secure"):
                self.environment.update({"elasticsearch.{}".format(cfg): default_creds.get(cfg)})

    def _content(self):
        return dict(
            depends_on=self.depends_on,
            environment=self.environment,
            healthcheck=curl_healthcheck(
                self.SERVICE_PORT, "enterprise-search", path="/", retries=20),
            labels=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class Kibana(StackService, Service):
    default_environment = {
        "SERVER_HOST": "0.0.0.0",
        "SERVER_NAME": "kibana.example.org",
    }

    SERVICE_PORT = 5601

    def __init__(self, **options):
        super(Kibana, self).__init__(**options)

        if not self.at_least_version("6.3") and not self.oss:
            self.docker_name = self.name() + "-x-pack"
        self.environment = self.default_environment.copy()

        self.kibana_tls = self.options.get("kibana_enable_tls", False)
        self.es_tls = options.get("elasticsearch_enable_tls", False)
        self.kibana_yml = options.get("kibana_yml")
        default_es_hosts = self.default_elasticsearch_hosts(tls=self.es_tls)
        urls = self.options.get("kibana_elasticsearch_urls") or [default_es_hosts]
        self.environment["ELASTICSEARCH_HOSTS"] = ",".join(urls)
        use_local_package_registry = options.get("enable_package_registry")
        self.depends_on = {"elasticsearch": {"condition": "service_healthy"}} if self.options.get(
            "enable_elasticsearch", True) else {}

        if options.get('kibana_verbose'):
            self.environment["LOGGING_VERBOSE"] = "true"
        if not self.oss:
            self.environment["XPACK_MONITORING_ENABLED"] = "true"
            if self.at_least_version("6.3"):
                self.environment["XPACK_XPACK_MAIN_TELEMETRY_ENABLED"] = "false"
            if self.at_least_version("7.5"):
                self.environment["TELEMETRY_ENABLED"] = "false"
            if self.at_least_version("7.7"):
                self.environment["XPACK_SECURITY_ENCRYPTIONKEY"] = "fhjskloppd678ehkdfdlliverpoolfcr"
                self.environment["XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY"] = "fhjskloppd678ehkdfdlliverpoolfcr"
            if self.at_least_version("7.8"):
                self.environment["XPACK_FLEET_AGENTS_ELASTICSEARCH_HOST"] = urls[0]
                self.environment["XPACK_FLEET_AGENTS_KIBANA_HOST"] = "{}://kibana:{}".format(
                    "https" if self.kibana_tls else "http", self.SERVICE_PORT)
            if options.get("xpack_secure"):
                self.environment["ELASTICSEARCH_PASSWORD"] = "changeme"
                self.environment["ELASTICSEARCH_USERNAME"] = "kibana_system_user"
                self.environment["STATUS_ALLOWANONYMOUS"] = "true"
                if self.at_least_version("7.6"):
                    self.environment["XPACK_SECURITY_LOGINASSISTANCEMESSAGE"] = (
                        "Login&#32;details:&#32;`{}/{}`.&#32;Further&#32;details&#32;[here]({}).").format(
                        "admin", self.environment["ELASTICSEARCH_PASSWORD"],
                        "https://github.com/elastic/apm-integration-testing#logging-in")
            if self.at_least_version("7.6"):
                if not options.get("no_kibana_apm_servicemaps"):
                    self.environment["XPACK_APM_SERVICEMAPENABLED"] = "true"
            if self.kibana_tls:
                certs = "/usr/share/kibana/config/certs/tls.crt"
                certsKey = "/usr/share/kibana/config/certs/tls.key"
                caCerts = "/usr/share/kibana/config/certs/ca.crt"
                self.environment["SERVER_SSL_ENABLED"] = "true"
                self.environment["SERVER_SSL_CERTIFICATE"] = certs
                self.environment["SERVER_SSL_KEY"] = certsKey
                self.environment["ELASTICSEARCH_SSL_CERTIFICATEAUTHORITIES"] = caCerts
            elif self.version_lower_than("7.13"):
                if self.at_least_version("7.10"):
                    self.environment["XPACK_FLEET_AGENTS_TLSCHECKDISABLED"] = "true"
                elif self.at_least_version("7.9"):
                    self.environment["XPACK_INGESTMANAGER_FLEET_TLSCHECKDISABLED"] = "true"
            url = package_registry_url(options)
            if url:
                self.environment["XPACK_FLEET_REGISTRYURL"] = url
            if use_local_package_registry:
                self.depends_on["package-registry"] = {"condition": "service_healthy"}
        if self.at_least_version("8.0"):
            self.environment["ENTERPRISESEARCH_HOST"] = "http://enterprise-search:" + str(EnterpriseSearch.SERVICE_PORT)

    @classmethod
    def add_arguments(cls, parser):
        super(Kibana, cls).add_arguments(parser)
        parser.add_argument(
            "--kibana-verbose",
            action="store_true",
            help="Enable Kibana verbose logging"
        )
        parser.add_argument(
            "--kibana-elasticsearch-url",
            action="append",
            dest="kibana_elasticsearch_urls",
            help="kibana elasticsearch output url(s)."
        )

        parser.add_argument(
            '--kibana-enable-tls',
            action="store_true",
            dest="kibana_enable_tls",
            help="kibana enable TLS with pre-configured self-signed certificates.",
        )

        parser.add_argument(
            '--kibana-yml',
            const="./docker/kibana/kibana.yml",
            nargs="?",
            help='override kibana.yml'
        )

        parser.add_argument(
            "--no-kibana-apm-servicemaps",
            action="store_true",
            help="disable the APM service maps UI",
        )

        parser.add_argument(
            "--kibana-src",
            nargs="?",
            help="Use Kibana source folder to run Kibana from sources.",
        )

        parser.add_argument(
            "--kibana-src-start-cmd",
            nargs="?",
            help="Command used to start Kibana from sources " +
                 "(yarn kbn bootstrap && yarn start " +
                 "-c /usr/share/kibana/config/kibana_src.yml " +
                 "-c /usr/share/kibana/config/kibana.yml).",
            default="yarn kbn bootstrap && yarn start " +
                    "-c /usr/share/kibana/config/kibana_src.yml " +
                    "-c /usr/share/kibana/config/kibana.yml " +
                    "--no-dev-config"
        )

    def _content(self):
        volumes = []

        if self.kibana_tls:
            volumes.extend([
                "./scripts/tls/kibana/kibana.crt:/usr/share/kibana/config/certs/tls.crt",
                "./scripts/tls/kibana/kibana.key:/usr/share/kibana/config/certs/tls.key",
                "./scripts/tls/ca/ca.crt:/usr/share/kibana/config/certs/ca.crt"
            ])

        if self.options.get("kibana_src"):
            kibana_src = self.options.get("kibana_src")
            volumes.extend([
                "{}:/usr/share/kibana".format(kibana_src),
                "./docker/kibana_src/kibana_src.yml:/usr/share/kibana/config/kibana_src.yml"
            ])

        if self.kibana_yml:
            volumes.append("{}:/usr/share/kibana/config/kibana.yml".format(self.kibana_yml))

        content = dict(
            healthcheck=curl_healthcheck(
                self.SERVICE_PORT, "kibana", path="/api/status", retries=30, https=self.kibana_tls, start_period="10s"),
            depends_on=self.depends_on,
            environment=self.environment,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )

        if volumes:
            content["volumes"] = volumes

        if self.options.get("kibana_src"):
            with open("{}/.node-version".format(kibana_src), 'r') as file:
                node_version = file.read().replace('\n', '')
            content["build"] = dict(
                context="docker/kibana_src",
                dockerfile="Dockerfile",
                args=[
                    "NODE_VERSION={}".format(node_version.replace('\n', '')),
                    "UID={}".format(os.getuid()),
                    "GID={}".format(os.getgid()),
                ])
            content["image"] = "kibana_src"
            content["working_dir"] = "/usr/share/kibana"
            content["command"] = "'{}'".format(self.options.get("kibana_src_start_cmd"))
            self.environment["NODE_OPTIONS"] = "--max-old-space-size=4096"
            self.environment["BABEL_DISABLE_CACHE"] = "true"
            self.environment["HOME"] = "/usr/share/kibana"
            content["healthcheck"] = curl_healthcheck(
                self.SERVICE_PORT, "kibana", path="/api/status", retries=300, https=self.kibana_tls)
        return content

    @staticmethod
    def enabled():
        return True


def package_registry_url(options):
    """
    package_registry_url returns the Elastic Package Registry URL to configure
    in the managed APM Server service, and Kibana service.
    """
    url = options.get("package_registry_url", "")
    if url:
        return url
    if options.get("enable_package_registry"):
        return "http://package-registry:{}".format(PackageRegistry.SERVICE_PORT)
    elif options.get("snapshot") or not options.get("release"):
        return "https://epr-snapshot.elastic.co"
    # default to production
    return ""
