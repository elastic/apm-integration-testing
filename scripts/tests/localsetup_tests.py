from __future__ import print_function


import io
import sys
import unittest
import collections
import yaml

from .. import compose

from ..compose import (OpbeansPython, OpbeansRum, OpbeansGo, OpbeansJava,
                       OpbeansNode, OpbeansRuby, OpbeansLoadGenerator)

from ..compose import (ApmServer, Kibana, Elasticsearch)

from ..compose import (Postgres, Redis)

from ..compose import LocalSetup, discover_services, parse_version

from .service_tests import ServiceTest

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


if sys.version_info[0] == 3:
    stringIO = io.StringIO
else:
    stringIO = io.BytesIO


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
                      - "127.0.0.1:3003:3000"
                    environment:
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_JS_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTIC_APM_SAMPLE_RATE=1
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_CACHE=redis://redis:6379
                      - OPBEANS_PORT=3000
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
                      - "127.0.0.1:3002:3000"
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
                      - OPBEANS_SERVER_PORT=3000
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
                      test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-java:3000/"]
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
                        - ELASTIC_APM_JS_SERVER_URL=http://apm-server:8200
                        - ELASTIC_APM_APP_NAME=opbeans-node
                        - ELASTIC_APM_SERVICE_NAME=opbeans-node
                        - ELASTIC_APM_LOG_LEVEL=info
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
                        - ELASTIC_APM_JS_SERVER_URL=http://apm-server:8200
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
                      - "127.0.0.1:3001:3000"
                    environment:
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_SERVICE_NAME=opbeans-ruby
                      - DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby
                      - REDIS_URL=redis://redis:6379
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_SERVER_URL=http://opbeans-ruby:3000
                      - RAILS_ENV=production
                      - RAILS_LOG_TO_STDOUT=1
                      - PORT=3000
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
                      test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--silent", "--output", "/dev/null", "http://opbeans-ruby:3000/"]
                      interval: 5s
                      retries: 100""")  # noqa: 501

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

    def test_opbeans_loadgen(self):
        opbeans_load_gen = OpbeansLoadGenerator(
            version="6.3.1",
            enable_opbeans_python=True,
            enable_opbeans_node=True,
            no_opbeans_node_loadgen=True,
        ).render()
        assert opbeans_load_gen == yaml.load("""
            opbeans-load-generator:
                image: opbeans/opbeans-loadgen:latest
                container_name: localtesting_6.3.1_opbeans-load-generator
                depends_on:
                    opbeans-python: {condition: service_healthy}
                environment: ['OPBEANS_URLS=opbeans-python:http://opbeans-python:3000']
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}""")


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


#
# Local setup tests
#
class LocalTest(unittest.TestCase):
    maxDiff = None

    def test_service_registry(self):
        registry = discover_services()
        self.assertIn(ApmServer, registry)

    def test_start_6_2_default(self):
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
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, xpack.monitoring.enabled=true, -E, setup.dashboards.enabled=true,
                    -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_6.2.10_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                    kibana: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://localhost:8200/healthcheck']
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

    def test_start_6_3_default(self):
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
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, xpack.monitoring.enabled=true, -E, setup.dashboards.enabled=true,
                    -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_6.3.10_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                    kibana: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://localhost:8200/healthcheck']
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

    def test_start_master_default(self):
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
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, 'setup.kibana.host=kibana:5601', -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, xpack.monitoring.enabled=true, -E, setup.dashboards.enabled=true,
                    -E, output.elasticsearch.enabled=true, -E, 'output.elasticsearch.hosts=[elasticsearch:9200]']
                container_name: localtesting_7.0.10-alpha1_apm-server
                depends_on:
                    elasticsearch: {condition: service_healthy}
                    kibana: {condition: service_healthy}
                healthcheck:
                    interval: 5s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', --silent, --output, /dev/null, 'http://localhost:8200/healthcheck']
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

    @mock.patch(compose.__name__ + '.load_images')
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

    @mock.patch(compose.__name__ + '.load_images')
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

    @mock.patch(compose.__name__ + '.load_images')
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

    @mock.patch(compose.__name__ + '.load_images')
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

    @mock.patch(compose.__name__ + '.load_images')
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
            # post-6.3
            Case(Elasticsearch, "https://staging.elastic.co/6.3.10-be84d930/docker/elasticsearch-6.3.10.tar.gz",
                 dict(bc="be84d930", version="6.3.10")),
            Case(Elasticsearch, "https://staging.elastic.co/6.3.10-be84d930/docker/elasticsearch-oss-6.3.10.tar.gz",
                 dict(bc="be84d930", oss=True, version="6.3.10")),
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
