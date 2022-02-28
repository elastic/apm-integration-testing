#
# Opbeans Services
#

from collections import OrderedDict

from .helpers import add_agent_environment, curl_healthcheck, wget_healthcheck, dyno
from .service import Service, DEFAULT_APM_SERVER_URL, DEFAULT_APM_JS_SERVER_URL, DEFAULT_SERVICE_VERSION


class OpbeansService(Service):
    APPLICATION_PORT = 3000
    DEFAULT_SAMPLE_RATE = 10

    def __init__(self, **options):
        super(OpbeansService, self).__init__(**options)
        self.apm_server_url = options.get("apm_server_url", DEFAULT_APM_SERVER_URL)
        self.apm_js_server_url = options.get("opbeans_apm_js_server_url", DEFAULT_APM_JS_SERVER_URL)
        self.opbeans_dt_probability = options.get("opbeans_dt_probability", 0.5)
        if hasattr(self, "DEFAULT_SERVICE_NAME"):
            self.service_name = options.get(self.option_name() + "_service_name", self.DEFAULT_SERVICE_NAME)
        self.service_version = options.get(self.option_name() + "_service_version", DEFAULT_SERVICE_VERSION)
        self.agent_branch = options.get(self.option_name() + "_agent_branch") or ""
        self.agent_repo = options.get(self.option_name() + "_agent_repo") or ""
        self.agent_local_repo = options.get(self.option_name() + "_agent_local_repo")
        self.opbeans_branch = options.get(self.option_name() + "_branch") or ""
        self.opbeans_repo = options.get(self.option_name() + "_repo") or ""
        self.sample_rate = float(int(options.get(self.option_name() + "_sample_rate") or 1) / 10)
        self.es_urls = ",".join(self.options.get("opbeans_elasticsearch_urls") or
                                [self.DEFAULT_ELASTICSEARCH_HOSTS_NO_TLS])
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
        parser.add_argument(
            '--' + cls.name() + '-service-version',
            default=None,
            dest=cls.option_name() + '_service_version',
            help=cls.name() + " service version"
        )
        parser.add_argument(
            '--' + cls.name() + '-sample-rate',
            default=cls.DEFAULT_SAMPLE_RATE,
            dest=cls.option_name() + '_sample_rate',
            help=cls.name() + " sample rate percentage",
            choices=range(1, 101)
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
    DEFAULT_AGENT_BRANCH = "main"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-dotnet"
    DEFAULT_SERVICE_NAME = "opbeans-dotnet"
    DEFAULT_AGENT_VERSION = ""
    DEFAULT_OPBEANS_BRANCH = "main"
    DEFAULT_OPBEANS_REPO = "elastic/opbeans-dotnet"
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"
    DEFAULT_SAMPLE_RATE = 10

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
                "ELASTIC_APM_SERVICE_VERSION={}".format(self.service_version),
                "ELASTIC_APM_SERVER_URLS={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.APPLICATION_PORT, "opbeans-dotnet", path="/", retries=36),
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
        )
        return content


class OpbeansDotnet01(OpbeansDotnet):
    SERVICE_PORT = 3104
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "testing"

    def __init__(self, **options):
        super(OpbeansDotnet01, self).__init__(**options)


class OpbeansGo(OpbeansService):
    SERVICE_PORT = 3003
    DEFAULT_AGENT_BRANCH = "1.x"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-go"
    DEFAULT_OPBEANS_BRANCH = "1.x"
    DEFAULT_OPBEANS_REPO = "elastic/opbeans-go"
    DEFAULT_SERVICE_NAME = "opbeans-go"
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"
    DEFAULT_SAMPLE_RATE = 10

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
                "ELASTIC_APM_SERVICE_VERSION={}".format(self.service_version),
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_CACHE=redis://redis:6379",
                "OPBEANS_PORT={}".format(self.APPLICATION_PORT),
                "PGHOST=postgres",
                "PGPORT=5432",
                "PGUSER=postgres",
                "PGPASSWORD=verysecure",
                "PGSSLMODE=disable",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
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
    DEFAULT_SAMPLE_RATE = 10

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
        parser.add_argument(
            '--' + cls.name() + '-no-infer-spans',
            action="store_true",
            help=cls.name() + " disable inferred span collection",
        )

    def __init__(self, **options):
        super(OpbeansJava, self).__init__(**options)
        self.opbeans_image = options.get('opbeans_java_image')
        self.opbeans_version = options.get('opbeans_java_version')
        self.infer_spans = self._resolve_span_setting(options)

    def _resolve_span_setting(self, options):
        return not options.get('opbeans_java_no_infer_spans')

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN")
    ])
    @dyno({"DATABASE_URL": "jdbc:postgresql://toxi/opbeans?user=postgres&password=verysecure",
           "REDIS_URL": "redis://toxi:6379"
           })
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
                "ELASTIC_APM_SERVICE_VERSION={}".format(self.service_version),
                "ELASTIC_APM_APPLICATION_PACKAGES=co.elastic.apm.opbeans",
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_ENABLE_LOG_CORRELATION=true",
                "DATABASE_URL=jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure",
                "DATABASE_DIALECT=POSTGRESQL",
                "DATABASE_DRIVER=org.postgresql.Driver",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_SERVER_PORT={}".format(self.APPLICATION_PORT),
                "JAVA_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.APPLICATION_PORT, "opbeans-java", path="/", retries=36),
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
        )
        if self.agent_local_repo:
            content["volumes"] = [
                "{}:/local-install".format(self.agent_local_repo),
            ]
        if self.infer_spans:
            content["environment"].append("ELASTIC_APM_PROFILING_INFERRED_SPANS_ENABLED=true")
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
    DEFAULT_SAMPLE_RATE = 10

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
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "ELASTIC_APM_LOG_LEVEL=info",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "WORKLOAD_ELASTIC_APM_APP_NAME=workload",
                "WORKLOAD_ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "WORKLOAD_DISABLED={}".format(self.options.get("no_opbeans_node_loadgen", False)),
                "OPBEANS_SERVER_PORT={}".format(self.APPLICATION_PORT),
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
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=wget_healthcheck(self.APPLICATION_PORT, "opbeans-node", path="/"),
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
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
    DEFAULT_SAMPLE_RATE = 10

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
    @dyno({"DATABASE_URL": "postgres://postgres:verysecure@toxi/opbeans",
           "REDIS_URL": "redis://toxi:6379"
           })
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
                "ELASTIC_APM_SERVICE_VERSION={}".format(self.service_version),
                "ELASTIC_APM_SERVER_URL={}".format(self.apm_server_url),
                "ELASTIC_APM_JS_SERVER_URL={}".format(self.apm_js_server_url),
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "ELASTIC_APM_FLUSH_INTERVAL=5",
                "ELASTIC_APM_TRANSACTION_MAX_SPANS=50",
                "ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5",
                "ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES",
                "ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_USER=opbeans_user",
                "OPBEANS_PASS=changeme",
                "OPBEANS_SERVER_URL=http://opbeans-python:{}".format(self.APPLICATION_PORT),
                "PYTHON_AGENT_BRANCH=" + self.agent_branch,
                "PYTHON_AGENT_REPO=" + self.agent_repo,
                "PYTHON_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            healthcheck=curl_healthcheck(self.APPLICATION_PORT, "opbeans-python", path="/"),
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
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
    DEFAULT_AGENT_BRANCH = "main"
    DEFAULT_AGENT_REPO = "elastic/apm-agent-ruby"
    DEFAULT_LOCAL_REPO = "."
    DEFAULT_SERVICE_NAME = "opbeans-ruby"
    DEFAULT_OPBEANS_IMAGE = 'opbeans/opbeans-ruby'
    DEFAULT_OPBEANS_VERSION = 'latest'
    DEFAULT_ELASTIC_APM_ENVIRONMENT = "production"
    DEFAULT_SAMPLE_RATE = 10

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
                "ELASTIC_APM_SERVICE_VERSION={}".format(self.service_version),
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
                "DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby",
                "REDIS_URL=redis://redis:6379",
                "ELASTICSEARCH_URL={}".format(self.es_urls),
                "OPBEANS_SERVER_URL=http://opbeans-ruby:{}".format(self.APPLICATION_PORT),
                "RAILS_ENV=production",
                "RAILS_LOG_TO_STDOUT=1",
                "PORT={}".format(self.APPLICATION_PORT),
                "RUBY_AGENT_BRANCH=" + self.agent_branch,
                "RUBY_AGENT_REPO=" + self.agent_repo,
                "RUBY_AGENT_VERSION",
                "OPBEANS_DT_PROBABILITY={:.2f}".format(self.opbeans_dt_probability),
                "ELASTIC_APM_ENVIRONMENT={}".format(self.service_environment),
                "ELASTIC_APM_TRANSACTION_SAMPLE_RATE={:.2f}".format(self.sample_rate),
            ],
            depends_on=depends_on,
            image=None,
            labels=None,
            # lots of retries as the ruby app can take a long time to boot
            healthcheck=wget_healthcheck(self.APPLICATION_PORT, "opbeans-ruby", path="/", retries=50),
            ports=[self.publish_port(self.port, self.APPLICATION_PORT)],
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
    # FIXME this might not work with dyno because we are inherting from Service
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
            default=3000,
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
                "ELASTIC_APM_VERIFY_SERVER_CERT={}".format(str(not self.options.get("no_verify_server_cert")).lower()),
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
        parser.add_argument(
            '--loadgen-no-ws',
            action='store_true',
            default=False,
            help='Disable the webserver mode and just run the load generator'
        )
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
        self.non_interactive = options.get("loadgen_no_ws")
        # create load for opbeans services
        run_all_opbeans = options.get('run_all_opbeans') or options.get('run_all')
        excluded = ('opbeans_load_generator', 'opbeans_rum', 'opbeans_node', 'opbeans_dotnet01', 'opbeans_go01',
                    'opbeans_java01', 'opbeans_node01', 'opbeans_python01', 'opbeans_ruby01')
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
            ports=["8999:8000"],
            depends_on={service: {'condition': 'service_healthy'} for service in self.loadgen_services},
            environment=[
                "OPBEANS_URLS={}".format(','.join('{0}:http://{0}:{1}'.format(s, OpbeansService.APPLICATION_PORT) for s in sorted(self.loadgen_services))),  # noqa: E501
                "OPBEANS_RPMS={}".format(','.join('{}:{}'.format(k, v) for k, v in sorted(self.loadgen_rpms.items())))
            ],
            labels=None,
        )

        if not self.non_interactive:
            content["environment"].insert(0, "WS=1")

        return content
