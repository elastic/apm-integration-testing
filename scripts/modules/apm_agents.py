#
# Agent Integration Test Services
#

from .helpers import curl_healthcheck, add_agent_environment
from .service import Service, DEFAULT_APM_SERVER_URL, DEFAULT_APM_LOG_LEVEL


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
        default_environment = {
            "ELASTIC_APM_SERVICE_NAME": "rum",
            "ELASTIC_APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
            "ELASTIC_APM_LOG_LEVEL": self.options.get("apm_log_level") or DEFAULT_APM_LOG_LEVEL
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        return dict(
            build=dict(
                context="docker/rum",
                dockerfile="Dockerfile",
                args=[
                    "RUM_AGENT_BRANCH=" + self.agent_branch,
                    "RUM_AGENT_REPO=" + self.agent_repo,
                    "APM_SERVER_URL=" + self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
                ]
            ),
            container_name="rum",
            image=None,
            labels=None,
            logging=None,
            environment=environment,
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
        default_environment = {
            "ELASTIC_APM_LOG_LEVEL": self.options.get("apm_log_level") or DEFAULT_APM_LOG_LEVEL,
            "ELASTIC_APM_API_REQUEST_TIME": "3s",
            "ELASTIC_APM_FLUSH_INTERVAL": "500ms",
            "ELASTIC_APM_SERVICE_NAME": "gonethttpapp",
            "ELASTIC_APM_TRANSACTION_IGNORE_NAMES": "healthcheck",
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

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
            environment=environment,
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
        default_environment = {
            "EXPRESS_PORT": str(self.SERVICE_PORT),
            "EXPRESS_SERVICE_NAME": "expressapp",
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
            "ELASTIC_APM_LOG_LEVEL": self.options.get("apm_log_level") or DEFAULT_APM_LOG_LEVEL,
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        return dict(
            build={"context": "docker/nodejs/express", "dockerfile": "Dockerfile"},
            command="bash -c \"npm install {} && node app.js\"".format(self.agent_package),
            container_name="expressapp",
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "expressapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            environment=environment,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )


class AgentPhpApache(Service):
    SERVICE_PORT = 8030
    DEFAULT_AGENT_VERSION = "master"
    DEFAULT_AGENT_RELEASE = ""
    DEFAULT_AGENT_REPO = "elastic/apm-agent-php"

    @classmethod
    def add_arguments(cls, parser):
        super(AgentPhpApache, cls).add_arguments(parser)
        parser.add_argument(
            "--php-agent-version",
            default=cls.DEFAULT_AGENT_VERSION,
            help='Use PHP agent version (master, 0.1, 0.2, ...)',
        )
        parser.add_argument(
            "--php-agent-release",
            default=cls.DEFAULT_AGENT_RELEASE,
            help='Use PHP agent release version (0.1, 0.2, ...)',
        )
        parser.add_argument(
            "--php-agent-repo",
            default=cls.DEFAULT_AGENT_REPO,
            help="GitHub repo to be used. Default: {}".format(cls.DEFAULT_AGENT_REPO),
        )

    def __init__(self, **options):
        super(AgentPhpApache, self).__init__(**options)
        self.agent_version = options.get("php_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_release = options.get("php_agent_release", self.DEFAULT_AGENT_RELEASE)
        self.agent_repo = options.get("php_agent_repo", self.DEFAULT_AGENT_REPO)
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
                "context": "docker/php/apache",
                "dockerfile": "Dockerfile",
                "args": {
                    "PHP_AGENT_BRANCH": self.agent_version,
                    "PHP_AGENT_VERSION": self.agent_release,
                    "PHP_AGENT_REPO": self.agent_repo,
                },
            },
            container_name="phpapacheapp",
            environment={
                "ELASTIC_APM_SERVICE_NAME": "phpapacheapp",
                "ELASTIC_APM_VERIFY_SERVER_CERT": "false" if self.options.get("no_verify_server_cert") else "true"
            },
            healthcheck=curl_healthcheck("80", "phpapacheapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, 80)],
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
        default_environment = {
            "DJANGO_PORT": self.SERVICE_PORT,
            "DJANGO_SERVICE_NAME": "djangoapp",
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        ret = dict(
            build={"context": "docker/python/django", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -q -U {} && python testapp/manage.py runserver 0.0.0.0:{}\"".format(
                self.agent_package, self.SERVICE_PORT),
            container_name="djangoapp",
            environment=environment,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "djangoapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
        if ('elastic-apm==5.1' not in self.agent_package and 'elastic-apm==4.' not in self.agent_package):
            ret["environment"]["ELASTIC_APM_VERIFY_SERVER_CERT"] = (
                str(not self.options.get("no_verify_server_cert")).lower())
        return ret


class AgentPythonFlask(AgentPython):
    SERVICE_PORT = 8001

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "APM_SERVER_URL"),
    ])
    def _content(self):
        default_environment = {
            "FLASK_SERVICE_NAME": "flaskapp",
            "GUNICORN_CMD_ARGS": "-w 4 -b 0.0.0.0:{}".format(self.SERVICE_PORT),
        }
        if self.options.get("apm_log_level"):
            default_environment["ELASTIC_APM_LOG_LEVEL"] = self.options.get("apm_log_level")

        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        ret = dict(
            build={"context": "docker/python/flask", "dockerfile": "Dockerfile"},
            command="bash -c \"pip install -q -U {} && gunicorn app:app\"".format(self.agent_package),
            container_name="flaskapp",
            image=None,
            labels=None,
            logging=None,
            environment=environment,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "flaskapp"),
            depends_on=self.depends_on,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
        if ('elastic-apm==5.1' not in self.agent_package and 'elastic-apm==4.' not in self.agent_package):
            ret["environment"]["ELASTIC_APM_VERIFY_SERVER_CERT"] = (
                str(not self.options.get("no_verify_server_cert")).lower())
        return ret


class AgentRubyRails(Service):
    DEFAULT_AGENT_REPO = "elastic/apm-agent-ruby"
    DEFAULT_AGENT_VERSION = "latest"
    DEFAULT_AGENT_VERSION_STATE = "release"
    DEFAULT_RUBY_VERSION = "latest"
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
        parser.add_argument(
            "--ruby-version",
            default=cls.DEFAULT_RUBY_VERSION,
            help='Use Ruby version (latest, 2, 3, ...)',
        )

    def __init__(self, **options):
        super(AgentRubyRails, self).__init__(**options)
        self.agent_version = options.get("ruby_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_version_state = options.get("ruby_agent_version_state", self.DEFAULT_AGENT_VERSION_STATE)
        self.agent_repo = options.get("ruby_agent_repo", self.DEFAULT_AGENT_REPO)
        self.ruby_version = options.get("ruby_version", self.DEFAULT_RUBY_VERSION)
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    def _map_log_level(self, lvl):
        """
        Resolves a standard log level such as 'info' to
        a specific log level string as required by the Ruby agent.
        See https://www.rubydoc.info/stdlib/logger/Logger/Severity
        and https://www.elastic.co/guide/en/apm/agent/ruby/1.x/configuration.html#config-log-level
        """

        if lvl == "trace":
            print("WARNING: Trace log level requested but not supported by Ruby agent. "
                  "Setting to debug and continuing.")
            return 0

        log_level_map = {
            "debug": 0,
            "info": 1,
            "warning": 2,
            "error": 3,
        }
        return log_level_map[lvl]

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
    ])
    def _content(self):
        default_environment = {
            "APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
            "ELASTIC_APM_LOG_LEVEL": self._map_log_level(
                self.options.get("apm_log_level").lower()
                if self.options.get("apm_log_level")
                else DEFAULT_APM_LOG_LEVEL
            ),
            "ELASTIC_APM_API_REQUEST_TIME": "3s",
            "ELASTIC_APM_SERVER_URL": self.options.get("apm_server_url", DEFAULT_APM_SERVER_URL),
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
            "ELASTIC_APM_SERVICE_NAME": "railsapp",
            "RAILS_PORT": self.SERVICE_PORT,
            "RAILS_SERVICE_NAME": "railsapp",
            "RUBY_AGENT_VERSION_STATE": self.agent_version_state,
            "RUBY_AGENT_VERSION": self.agent_version,
            "RUBY_AGENT_REPO": self.agent_repo,
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        return dict(
            build={
                "context": "docker/ruby/rails",
                "dockerfile": "Dockerfile",
                "args": {
                    "RUBY_AGENT_VERSION": self.agent_version,
                    "RUBY_AGENT_REPO": self.agent_repo,
                    "RUBY_VERSION": self.ruby_version,
                }
            },
            command="bash -c \"bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p {}\"".format(
                self.SERVICE_PORT),
            container_name="railsapp",
            environment=environment,
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
        parser.add_argument(
            '--java-m2-cache',
            action='store_true',
            dest='java_m2_cache',
            help='Use the local m2 cache (for speeding up the builds)',
            default=False
        )

    def __init__(self, **options):
        super(AgentJavaSpring, self).__init__(**options)
        self.agent_version = options.get("java_agent_version", self.DEFAULT_AGENT_VERSION)
        self.agent_release = options.get("java_agent_release", self.DEFAULT_AGENT_RELEASE)
        self.agent_repo = options.get("java_agent_repo", self.DEFAULT_AGENT_REPO)
        self.java_m2_cache = str(options.get("java_m2_cache", False)).lower()
        if options.get("enable_apm_server", True):
            self.depends_on = {
                "apm-server": {"condition": "service_healthy"},
            }

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URL"),
    ])
    def _content(self):
        default_environment = {
            "ELASTIC_APM_API_REQUEST_TIME": "3s",
            "ELASTIC_APM_SERVICE_NAME": "springapp",
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
            "ELASTIC_APM_LOG_LEVEL": self.options.get("apm_log_level") or DEFAULT_APM_LOG_LEVEL,
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

        default_args = {
            "JAVA_AGENT_BRANCH": self.agent_version,
            "JAVA_AGENT_BUILT_VERSION": self.agent_release,
            "JAVA_AGENT_REPO": self.agent_repo,
            "JAVA_M2_CACHE": self.java_m2_cache
        }

        return dict(
            build={
                "context": "docker/java/spring",
                "dockerfile": "Dockerfile",
                "args": default_args
            },
            container_name="javaspring",
            image=None,
            labels=None,
            logging=None,
            environment=environment,
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

    def _map_log_level(self, lvl):
        """
        Resolves a standard log level such as 'info' to
        a specific log level string as required by the .NET agent.

        See https://www.elastic.co/guide/en/apm/agent/dotnet/current/config-supportability.html#config-log-level
        """
        log_level_map = {
            "info": "Info",
            "error": "Error",
            "warning": "Warning",
            "debug": "Debug",
            "trace": "Trace"
        }
        return log_level_map[lvl]

    @add_agent_environment([
        ("apm_server_secret_token", "ELASTIC_APM_SECRET_TOKEN"),
        ("apm_server_url", "ELASTIC_APM_SERVER_URLS"),
    ])
    def _content(self):
        default_environment = {
            "ELASTIC_APM_VERIFY_SERVER_CERT": str(not self.options.get("no_verify_server_cert")).lower(),
            "ELASTIC_APM_API_REQUEST_TIME": "3s",
            "ELASTIC_APM_FLUSH_INTERVAL": "5",
            "ELASTIC_APM_SERVICE_NAME": "dotnetapp",
            "ELASTIC_APM_TRANSACTION_IGNORE_NAMES": "healthcheck",
            "ELASTIC_APM_LOG_LEVEL": self._map_log_level(
                self.options.get("apm_log_level").lower()
                if self.options.get("apm_log_level")
                else DEFAULT_APM_LOG_LEVEL
            ),
        }
        environment = default_environment
        if self.apm_api_key:
            environment.update(self.apm_api_key)

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
            environment=environment,
            healthcheck=curl_healthcheck(self.SERVICE_PORT, "dotnetapp"),
            depends_on=self.depends_on,
            image=None,
            labels=None,
            logging=None,
            ports=[self.publish_port(self.port, self.SERVICE_PORT)],
        )
