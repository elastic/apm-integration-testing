import argparse
import collections
import datetime
import glob
import inspect
import json
import logging
import os
import subprocess
import sys
import re

from .beats import BeatMixin
from .helpers import load_images, parse_version
from .opbeans import OpbeansService, OpbeansRum
from .service import Service, DEFAULT_APM_SERVER_URL
from .proxy import Toxi, Dyno

# these imports are used by discover_services function to discover services from modules loaded


from .beats import (  # noqa: F401
    Packetbeat, Metricbeat, Heartbeat, Filebeat
)
from .elastic_stack import (  # noqa: F401
    ApmManaged, ApmServer, ElasticAgent, Elasticsearch, EnterpriseSearch, Kibana, PackageRegistry
)
from .aux_services import (  # noqa: F401
    CommandService, Kafka, Logstash, Postgres, Redis, StatsD, Zookeeper, WaitService
)
from .opbeans import (  # noqa: F401
    OpbeansNode, OpbeansRuby, OpbeansPhp, OpbeansPython, OpbeansDotnet,
    OpbeansGo, OpbeansJava, OpbeansLoadGenerator, OpbeansGo01, OpbeansDotnet01,
    OpbeansJava01, OpbeansNode01, OpbeansPython01, OpbeansRuby01
)


PACKAGE_NAME = 'localmanager'
__version__ = "4.0.0"


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
        '6.8': '6.8.20',
        '7.0': '7.0.1',
        '7.1': '7.1.1',
        '7.2': '7.2.1',
        '7.3': '7.3.2',
        '7.4': '7.4.2',
        '7.5': '7.5.2',
        '7.6': '7.6.2',
        '7.7': '7.7.1',
        '7.8': '7.8.1',
        '7.9': '7.9.3',
        '7.10': '7.10.2',
        '7.11': '7.11.2',
        '7.12': '7.12.1',
        '7.13': '7.13.4',
        '7.14': '7.14.2',
        '7.15': '7.15.2',
        '7.16': '7.16.3',
        '7.17': '7.17.8',
        '8.1': '8.1.3',
        '8.2': '8.2.3',
        '8.3': '8.3.3',
        '8.4': '8.4.3',
        '8.5': '8.5.3',
        '8.6': '8.6.2',
        '8.7': '8.7.1',
        '8.8': '8.8.1',
        '8.9': '8.9.0',
        '8.10': '8.10.0',
        # UPDATECLI_AUTOMATION
        "main": "8.10.0",
        "master": "8.10.0",  # keep master alias for backward compatibility. Upgrade the main alias only
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
            'reset-enterprise-search-password',
            help="Resets enterprise search password.",
            description="Resets enterprise search password."
        ).set_defaults(func=self.reset_enterprise_search_password_handler)

        subparsers.add_parser(
            'status',
            help="Prints status of all services.",
            description="Prints the container status for each running service."
        ).set_defaults(func=self.status_handler)

        subparsers.add_parser(
            'load-dashboards',
            help="Loads APM dashboards into Kibana using APM Server.",
            description="Loads APM dashboards into Kibana using APM Server. APM Server, Elasticsearch, and Kibana must "
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

        self.init_build_parser(
            subparsers.add_parser(
                'build',
                help="Build the stack. See `build --help` for options.",
                description="Build the stack. Use the arguments to specify which "
                            "services to build. "
            ),
            services,
            argv=argv,
        ).set_defaults(func=self.build_handler)

        self.init_sourcemap_parser(
            subparsers.add_parser(
                'upload-sourcemap',
                help="Uploads sourcemap to the APM Server"
            )
        ).set_defaults(func=self.upload_sourcemaps_handler)

        self.store_options(parser)

        self.args = parser.parse_args(argv)

        self.validate_options(self.args, parser)

        # py3
        if not hasattr(self.args, "func"):
            parser.error("command required")

    def set_docker_compose_path(self, dst):
        """override docker-compose-path argument, for tests"""
        self.args.__setattr__("docker_compose_path", dst)

    def __call__(self):
        self.args.func()

    def init_build_parser(self, parser, services, argv=None):
        return self.init_build_start_parser(parser, services, argv)

    def init_start_parser(self, parser, services, argv=None):
        return self.init_build_start_parser(parser, services, argv)

    def init_build_start_parser(self, parser, services, argv=None):
        if not argv:
            argv = sys.argv
        available_versions = ' / '.join(list(self.SUPPORTED_VERSIONS))
        help_text = (
            "Which version of the stack to start. " + "Available options: {0}".format(available_versions)
        )
        parser.add_argument("stack-version", action='store', help=help_text)

        # Add a --no-x / --with-x argument for each service
        enabled_group = None
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
        if enabled_group:
            enabled_group.add_argument(
                '--no-opbeans-load-generator',
                action='store_true',
                dest='disable_opbeans_load_generator',
                help='Disable opbeans-load-generator',
                default=False,
            )

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
            '--no-download',
            '--skip-download',
            action='store_true',
            dest='skip_download',
            help='Skip the download of fresh images and use current ones'
        )

        # option for path to docker-compose.yml
        parser.add_argument(
            '--docker-compose-path',
            type=argparse.FileType(mode='w'),
            default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'docker-compose.yml')),
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
            '--ubi8',
            action='store_true',
            help='use ubi8 container images',
            dest='ubi8',
            default=False,
        )

        parser.add_argument(
            "--apm-server-url",
            action="store",
            help="apm server url to use for all clients",
            default=DEFAULT_APM_SERVER_URL,
        )

        parser.add_argument(
            "--apm-log-level",
            action="store",
            help="APM log level to use",
            choices=["off", "error", "warn", "info", "debug", "trace"],
        )

        parser.add_argument(
            "--index-suffix",
            action="store",
            help="index suffix to add to all event indices",
            default="",
        )

        parser.add_argument(
            '--opbeans-apm-js-server-url',
            action='store',
            help='server_url to use for Opbeans frontend service',
            dest='opbeans_apm_js_server_url',
            default=DEFAULT_APM_SERVER_URL,
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
            '--no-xpack-secure',
            action="store_false",
            dest="xpack_secure",
            help="disable xpack security throughout the stack",
        )

        parser.add_argument(
            '--no-verify-server-cert',
            action='store_true',
            dest='no_verify_server_cert',
            help='Define the environment variable ELASTIC_APM_VERIFY_SERVER_CERT=false' +
                 ' to disable the APM Server certificate verification.',
            default="false"
        )

        parser.add_argument(
            '--output-format',
            choices=("json", "yaml"),
            help='Select the output format for the docker-compose.yml file.',
            default="json"
        )

        parser.add_argument(
            '--dyno',
            action='store_true',
            help='All various services to be dynamically tuned to introduce latency or other pressure',
            default=False
        )

        parser.add_argument(
            '--package-registry-url',
            action="store",
            help="Elastic Package Registry URL to use for fetching integration packages",
        )

        self.store_options(parser)

        return parser

    def run_docker_compose_process(self, docker_compose_cmd):
        try:
            subprocess.check_call(docker_compose_cmd)
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

    def validate_options(self, args, parser):
        """
        Helper method to validate if certain options are compatible or not.
        """
        if hasattr(self.args, "oss") and hasattr(self.args, "ubi8") and args.oss and args.ubi8:
            parser.error("oss and ubi8 options are incompatible. Choose one of them instead.")

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
        print("{}".format("\n".join(sorted(self.available_options))))

    def build_handler(self):
        self.build_start_handler("build")

    def start_handler(self):
        self.build_start_handler("start")

    def build_start_handler(self, action):
        args = vars(self.args)

        if "version" not in args:
            # use stack-version directly if not supported, to allow use of specific releases, eg 6.2.3
            args["version"] = self.SUPPORTED_VERSIONS.get(args["stack-version"], args["stack-version"])

        if(parse_version(args["version"]) >= parse_version("8.0")):
            args["enable_apm_managed"] = True

        if args.get("enable_apm_server") is False:
            args["enable_apm_managed"] = False

        if args.get("enable_apm_managed", False):
            args["enable_apm_server"] = False
            if not args.get("enable_kibana", True):
                print("Kibana will be launched to configure APM integration and stopped after that.")
                args["enable_kibana"] = True
                args["shutdown_kibana"] = True

        if args.get("apm_server_enable_tls"):
            args["apm_server_url"] = args.get("apm_server_url", DEFAULT_APM_SERVER_URL).replace("http:", "https:")
            args["opbeans_apm_js_server_url"] = args["apm_server_url"]

        selections = set()
        run_all = args.get("run_all")
        all_opbeans = args.get('run_all_opbeans') or run_all
        any_opbeans = all_opbeans or any(v and k.startswith('enable_opbeans_') for k, v in args.items())
        opbeans_sidecars = ['postgres', 'redis', 'opbeans-load-generator']
        opbeans_2nds = ('opbeans-go01', 'opbeans-java01', 'opbeans-python01', 'opbeans-ruby01', 'opbeans-dotnet01',
                        'opbeans-node01')
        for service in self.services:
            service_enabled = args.get("enable_" + service.option_name())
            is_opbeans_service = issubclass(service, OpbeansService) or service is OpbeansRum
            is_opbeans_sidecar = service.name() in opbeans_sidecars
            is_opbeans_2nd = service.name() in opbeans_2nds
            is_obs = issubclass(service, BeatMixin)
            if (service_enabled or
                    (all_opbeans and is_opbeans_service and not is_opbeans_2nd) or
                    (any_opbeans and is_opbeans_sidecar and not is_opbeans_2nd) or
                    (run_all and is_obs and not is_opbeans_2nd)):
                selections.add(service(**args))

        if args.get('dyno'):
            toxi = Toxi()
            selections.add(toxi)
            toxi.gen_ports(selections)
            c = toxi.gen_config(selections)
            this_dir = os.path.dirname(os.path.realpath(__file__))
            toxi_cfg_path = os.path.join(this_dir, "../../docker/toxi/toxi.cfg")
            with open(toxi_cfg_path, 'w') as fh_:
                fh_.write(c)
            dyno = Dyno()
            selections.add(dyno)
            statsd = StatsD()
            selections.add(statsd)

        # freeze wait service selections here, future modifications of selections will not impact the wait service
        selections.add(WaitService(set(selections), **args))

        # any image with curl
        curl_image = "docker.elastic.co/elasticsearch/elasticsearch:8.0.0-SNAPSHOT"
        for c, snapshot_repo in enumerate(args.get("elasticsearch_snapshot_repo", [])):
            if not snapshot_repo.startswith("http"):
                print("skipping setup of non-http(s) repo: {}".format(snapshot_repo))
                continue
            if not snapshot_repo.endswith("/"):
                print("http(s) repo should probably end with '/': {}".format(snapshot_repo))
            repo_label = "repo{:d}".format(c)
            cmd = [
                "curl", "-X", "PUT",
                "-H", "Content-Type: application/json",
                "-d",
                json.dumps({"type": "url", "settings": {"url": snapshot_repo}}),
                # es creds + url only usable with default setup
                "http://admin:changeme@elasticsearch:9200/_snapshot/{:s}".format(repo_label),
            ]
            selections.add(CommandService(cmd, service=repo_label, image=curl_image, depends_on=["elasticsearch"]))

        # Add a container to call the Fleet setup API. This is necessary for installing the APM integration.
        if args.get("enable_kibana") and not args.get("enable_apm_managed", False):
            kibana_scheme = "https" if args.get("kibana_enable_tls", False) else "http"
            kibana_url = kibana_scheme + "://admin:changeme@kibana:5601"
            cmd = ["curl", "-X", "POST", "-H", "kbn-xsrf: 1", kibana_url + "/api/fleet/setup"]
            selections.add(CommandService(cmd, service="fleet_setup", image=curl_image, depends_on=["kibana"]))

        # `docker load` images if necessary, usually only for build candidates
        services_to_load = {}
        for service in selections:
            download_url = service.image_download_url()
            if download_url:
                services_to_load[list(service.render().keys())[0]] = download_url
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

        loadgen = services.get("opbeans-load-generator")
        if loadgen is not None:
            enabled_opbeans = any(re.search('OPBEANS_URLS=.+', v) for v in loadgen["environment"])
            if args.get("disable_opbeans_load_generator") or not enabled_opbeans:
                del services["opbeans-load-generator"]

        compose = dict(
            version="2.4",
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

        if args.get("output_format") == 'yaml':
            try:
                import yaml
            except ImportError:
                print("Failed to import 'yaml': pip install yaml, or specify an alternative --output-format.")
                sys.exit(1)
            yaml.dump(compose, docker_compose_path,
                      explicit_start=True,
                      default_flow_style=False,
                      indent=2
                      )
        elif args.get("output_format") == 'json':
            json.dump(compose, docker_compose_path, indent=2, sort_keys=True)
        docker_compose_path.flush()

        # try to figure out if writing to a real file, not amazing
        if hasattr(docker_compose_path, "name") and os.path.isdir(os.path.dirname(docker_compose_path.name)):
            docker_compose_path.close()
            print("Starting/Building stack services..\n")
            docker_compose_cmd = ["docker-compose", "-f", docker_compose_path.name]
            if not sys.stdin.isatty() and action not in ["build"]:
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
            if args.get("kibana_src"):
                image_services.remove('kibana')

            if image_services and not args["skip_download"]:
                pull_params = ["pull"]
                if not sys.stdin.isatty():
                    pull_params.extend(["-q"])
                self.run_docker_compose_process(docker_compose_cmd + pull_params + image_services)

            # really start
            if action in ["start"]:
                up_params = ["up", "-d"]
                if args["remove_orphans"]:
                    up_params.append("--remove-orphans")
            if action in ["build"]:
                up_params = ["build"]
            if not sys.stdin.isatty() and action not in ["build"]:
                up_params.extend(["--quiet-pull"])
            self.run_docker_compose_process(docker_compose_cmd + up_params)
            if args.get("shutdown_kibana", False):
                print("Stopping Kibana after configuring APM integration.")
                self.run_docker_compose_process(docker_compose_cmd + ["stop", "kibana"])

    @staticmethod
    def reset_enterprise_search_password_handler():
        subprocess.call(["docker-compose", "exec", "enterprise-search", "/usr/local/bin/docker-entrypoint.sh",
                         "--reset-auth"])

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
                g = os.path.abspath(os.path.join(os.path.dirname(
                    __file__),
                    '../../docker/opbeans/node/sourcemaps/*.map')
                )
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
            '-F sourcemap=@{sourcemap_file} '
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
        print(cmd)
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
                print('\tContainer "{}" is not running or an error occurred running: {}'.format(name, command))
                return False

            return output

        def print_elasticsearch_version(container):
            print("\nElasticsearch (image built: %s UTC):" % container.created)

            version = run_container_command(
                'elasticsearch', './bin/elasticsearch --version'
            )

            if version:
                print("\t{0}".format(version))

        def print_apm_server_version(container):
            print("\nAPM Server (image built: %s UTC):" % container.created)

            version = run_container_command('apm-server', 'apm-server version')

            if version:
                print("\t{0}".format(version))

        def print_apm_managed_version(container):
            print("\nElastic Agent managed APM Server (image built: %s UTC):" % container.created)

            version = run_container_command('apm-server',
                                            '/usr/share/elastic-agent/elastic-agent version --binary-only')

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

        def print_opbeans_node_version(_):
            print("\nAgent version (in opbeans-node):")

            version = run_container_command(
                'opbeans-node', 'npm list | grep elastic-apm-node'
            )

            if version:
                version = version.replace('+-- elastic-apm-node@', '')
                print("\t{0}".format(version))

        def print_opbeans_python_version(_):
            print("\nAgent version (in opbeans-python):")

            version = run_container_command(
                'opbeans-python', 'pip freeze | grep elastic-apm'
            )

            if version:
                version = version.replace('elastic-apm==', '')
                print("\t{0}".format(version))

        def print_opbeans_ruby_version(_):
            print("\nAgent version (in opbeans-ruby):")

            version = run_container_command(
                'opbeans-ruby', 'gem list | grep elastic-apm'
            )

            if version:
                version = version.replace('elastic-apm (*+)', '\1')
                print("\t{0}".format(version))

        dispatch = {
            'apm-server': print_apm_server_version,
            'apm-managed': print_apm_managed_version,
            'elasticsearch': print_elasticsearch_version,
            'kibana': print_kibana_version,
            'opbeans-node': print_opbeans_node_version,
            'opbeans-python': print_opbeans_python_version,
            'opbeans-ruby': print_opbeans_ruby_version,
        }
        for service_name, container in running_versions.items():
            print_version = dispatch.get(service_name)
            if not print_version:
                print("unknown version for", service_name)
                continue
            print_version(container)
