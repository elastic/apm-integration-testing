import json
import os

from .helpers import curl_healthcheck
from .service import StackService, Service


class BeatMixin(object):
    DEFAULT_OUTPUT = "elasticsearch"
    OUTPUTS = {"elasticsearch", "logstash"}
    STACK_CA_PATH = "/usr/share/beats/config/certs/stack-ca.crt"

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

        self.es_tls = options.get("elasticsearch_enable_tls", False)
        self.kibana_tls = options.get("kibana_enable_tls", False)

        def add_es_config(args, prefix="output", tls=self.es_tls):
            """add elasticsearch configuration options."""
            es_urls = options.get("{}_elasticsearch_urls".format(self.name())) or \
                [self.default_elasticsearch_hosts(tls=self.kibana_tls)]
            default_beat_creds = {"username": "{}_user".format(self.name()), "password": "changeme"}
            args.append((prefix + ".elasticsearch.hosts", json.dumps(es_urls)))
            for cfg in ("username", "password"):
                es_opt = "{}_elasticsearch_{}".format(self.name(), cfg)
                if options.get(es_opt):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), options[es_opt]))
                elif options.get("xpack_secure"):
                    args.append((prefix + ".elasticsearch.{}".format(cfg), default_beat_creds.get(cfg)))
            if tls:
                args.append((prefix + ".elasticsearch.ssl.certificate_authorities", "['" + self.STACK_CA_PATH + "']"))

        command_args = []
        add_es_config(command_args)
        beat_output = options.get("{}_output".format(self.name()), self.DEFAULT_OUTPUT)
        if beat_output == "elasticsearch":
            command_args.extend([("output.elasticsearch.enabled", "true")])
        else:
            command_args.extend([("output.elasticsearch.enabled", "false")])
            add_es_config(command_args, prefix="monitoring" if self.at_least_version("7.2") else "xpack.monitoring")
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
                    ("output.kafka.topics", "[{default: '%s', topic: '%s'}]" % (self.name(), self.name())),
                ])

        if self.kibana_tls:
            command_args.extend([
                ("setup.kibana.protocol", "https"),
                ("setup.kibana.ssl.certificate_authorities", '["' + self.STACK_CA_PATH + '"]'),
            ])

        for param, value in command_args:
            self.command.extend(["-E", param + "=" + value])

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
        if self.at_least_version("7.2"):
            config = "filebeat.yml"
        elif self.at_least_version("6.1"):
            config = "filebeat.6.x-compat.yml"
        else:
            config = "filebeat.simple.yml"
        self.filebeat_config_path = os.path.join(".", "docker", "filebeat", config)

    def _content(self):
        return dict(
            command=self.command,
            depends_on=self.depends_on,
            environment=self.environment,
            labels=None,
            user="root",
            healthcheck=curl_healthcheck("5066", "localhost", path="/?pretty"),
            volumes=[
                self.filebeat_config_path + ":/usr/share/filebeat/filebeat.yml",
                "/var/lib/docker/containers:/var/lib/docker/containers",
                "/var/run/docker.sock:/var/run/docker.sock",
                "./scripts/tls/ca/ca.crt:" + self.STACK_CA_PATH,
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
            healthcheck=curl_healthcheck("5066", "localhost", path="/?pretty"),
            volumes=[
                self.heartbeat_config_path + ":/usr/share/heartbeat/heartbeat.yml",
                "/var/lib/docker/containers:/var/lib/docker/containers",
                "/var/run/docker.sock:/var/run/docker.sock",
                "./scripts/tls/ca/ca.crt:" + self.STACK_CA_PATH,
            ]
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
            healthcheck=curl_healthcheck("5066", "localhost", path="/?pretty"),
            volumes=[
                ("./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml"
                 if self.at_least_version("7.2")
                 else "./docker/metricbeat/metricbeat.6.x-compat.yml:/usr/share/metricbeat/metricbeat.yml"),
                "/var/run/docker.sock:/var/run/docker.sock",
                "./scripts/tls/ca/ca.crt:" + self.STACK_CA_PATH,
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
            healthcheck=curl_healthcheck("5066", "localhost", path="/?pretty"),
            volumes=[
                ("./docker/packetbeat/packetbeat.yml:/usr/share/packetbeat/packetbeat.yml"
                 if self.at_least_version("7.2")
                 else "./docker/packetbeat/packetbeat.6.x-compat.yml:/usr/share/packetbeat/packetbeat.yml"),
                "/var/run/docker.sock:/var/run/docker.sock",
                "./scripts/tls/ca/ca.crt:" + self.STACK_CA_PATH,
            ]
        )
