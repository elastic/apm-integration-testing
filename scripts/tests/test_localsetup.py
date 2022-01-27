from __future__ import print_function

import io
import sys
import unittest
import collections
import yaml
import os

from ..modules import cli
from ..modules import service
from ..modules.aux_services import Postgres, Redis
from ..modules.elastic_stack import ApmServer, Elasticsearch
from ..modules.helpers import parse_version
from ..modules.opbeans import (
    OpbeansService, OpbeansDotnet, OpbeansGo, OpbeansJava, OpbeansNode, OpbeansPython,
    OpbeansRuby, OpbeansRum, OpbeansLoadGenerator
)

from ..modules.cli import discover_services, LocalSetup

from .test_service import ServiceTest

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


def opbeans_services():
    return (cls for cls in discover_services() if issubclass(cls, OpbeansService))


class OpbeansServiceTest(ServiceTest):
    def test_opbeans_dotnet(self):
        opbeans_go = OpbeansDotnet(version="6.3.10").render()
        self.assertEqual(
            opbeans_go, yaml.safe_load("""
                opbeans-dotnet:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/dotnet
                      args:
                        - DOTNET_AGENT_BRANCH=main
                        - DOTNET_AGENT_REPO=elastic/apm-agent-dotnet
                        - DOTNET_AGENT_VERSION=
                        - OPBEANS_DOTNET_BRANCH=main
                        - OPBEANS_DOTNET_REPO=elastic/opbeans-dotnet
                    container_name: localtesting_6.3.10_opbeans-dotnet
                    ports:
                      - "127.0.0.1:3004:3000"
                    environment:
                      - ELASTIC_APM_SERVICE_NAME=opbeans-dotnet
                      - ELASTIC_APM_SERVICE_VERSION=9c2e41c8-fb2f-4b75-a89d-5089fb55fc64
                      - ELASTIC_APM_SERVER_URLS=http://apm-server:8200
                      - ELASTIC_APM_JS_SERVER_URL=http://localhost:8200
                      - ELASTIC_APM_VERIFY_SERVER_CERT=true
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_DT_PROBABILITY=0.50
                      - ELASTIC_APM_ENVIRONMENT=production
                      - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      apm-server:
                        condition:
                          service_healthy
                      elasticsearch:
                        condition:
                          service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://opbeans-dotnet:3000/"]
                        timeout: 5s
                        interval: 10s
                        retries: 36""")
        )

    def test_opbeans_dotnet_version(self):
        opbeans = OpbeansDotnet(opbeans_dotnet_version="1.0").render()["opbeans-dotnet"]
        value = [e for e in opbeans["build"]["args"] if e.startswith("DOTNET_AGENT_VERSION")]
        self.assertEqual(value, ["DOTNET_AGENT_VERSION=1.0"])

    def test_opbeans_dotnet_branch(self):
        opbeans = OpbeansDotnet(opbeans_dotnet_branch="1.x").render()["opbeans-dotnet"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_DOTNET_BRANCH")]
        self.assertEqual(branch, ["OPBEANS_DOTNET_BRANCH=1.x"])

    def test_opbeans_dotnet_repo(self):
        opbeans = OpbeansDotnet(opbeans_dotnet_repo="foo/bar").render()["opbeans-dotnet"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_DOTNET_REPO")]
        self.assertEqual(branch, ["OPBEANS_DOTNET_REPO=foo/bar"])

    def test_opbeans_go(self):
        opbeans_go = OpbeansGo(version="6.3.10").render()
        self.assertEqual(
            opbeans_go, yaml.safe_load("""
                opbeans-go:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/go
                      args:
                        - GO_AGENT_BRANCH=1.x
                        - GO_AGENT_REPO=elastic/apm-agent-go
                        - OPBEANS_GO_BRANCH=1.x
                        - OPBEANS_GO_REPO=elastic/opbeans-go
                    container_name: localtesting_6.3.10_opbeans-go
                    ports:
                      - "127.0.0.1:3003:3000"
                    environment:
                      - ELASTIC_APM_SERVICE_NAME=opbeans-go
                      - ELASTIC_APM_SERVICE_VERSION=9c2e41c8-fb2f-4b75-a89d-5089fb55fc64
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_JS_SERVER_URL=http://localhost:8200
                      - ELASTIC_APM_VERIFY_SERVER_CERT=true
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_CACHE=redis://redis:6379
                      - OPBEANS_PORT=3000
                      - PGHOST=postgres
                      - PGPORT=5432
                      - PGUSER=postgres
                      - PGPASSWORD=verysecure
                      - PGSSLMODE=disable
                      - OPBEANS_DT_PROBABILITY=0.50
                      - ELASTIC_APM_ENVIRONMENT=production
                      - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      postgres:
                        condition:
                          service_healthy
                      redis:
                        condition:
                          service_healthy
                      apm-server:
                        condition:
                          service_healthy
                      elasticsearch:
                        condition:
                          service_healthy
 """)  # noqa: 501
        )

    def test_opbeans_go_branch(self):
        opbeans = OpbeansGo(opbeans_go_branch="1.x").render()["opbeans-go"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_GO_BRANCH")]
        self.assertEqual(branch, ["OPBEANS_GO_BRANCH=1.x"])

    def test_opbeans_go_repo(self):
        opbeans = OpbeansGo(opbeans_go_repo="foo/bar").render()["opbeans-go"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_GO_REPO")]
        self.assertEqual(branch, ["OPBEANS_GO_REPO=foo/bar"])

    def test_opbeans_java(self):
        opbeans_java = OpbeansJava(version="6.3.10").render()
        self.assertEqual(
            opbeans_java, yaml.safe_load("""
                opbeans-java:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/java
                      args:
                        - JAVA_AGENT_BRANCH=
                        - JAVA_AGENT_REPO=elastic/apm-agent-java
                        - OPBEANS_JAVA_IMAGE=opbeans/opbeans-java
                        - OPBEANS_JAVA_VERSION=latest
                    container_name: localtesting_6.3.10_opbeans-java
                    ports:
                      - "127.0.0.1:3002:3000"
                    environment:
                      - ELASTIC_APM_SERVICE_NAME=opbeans-java
                      - ELASTIC_APM_SERVICE_VERSION=9c2e41c8-fb2f-4b75-a89d-5089fb55fc64
                      - ELASTIC_APM_APPLICATION_PACKAGES=co.elastic.apm.opbeans
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_VERIFY_SERVER_CERT=true
                      - ELASTIC_APM_FLUSH_INTERVAL=5
                      - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                      - ELASTIC_APM_ENABLE_LOG_CORRELATION=true
                      - DATABASE_URL=jdbc:postgresql://postgres/opbeans?user=postgres&password=verysecure
                      - DATABASE_DIALECT=POSTGRESQL
                      - DATABASE_DRIVER=org.postgresql.Driver
                      - REDIS_URL=redis://redis:6379
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_SERVER_PORT=3000
                      - JAVA_AGENT_VERSION
                      - OPBEANS_DT_PROBABILITY=0.50
                      - ELASTIC_APM_ENVIRONMENT=production
                      - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                      - ELASTIC_APM_PROFILING_INFERRED_SPANS_ENABLED=true
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      postgres:
                        condition:
                          service_healthy
                      apm-server:
                        condition:
                          service_healthy
                      elasticsearch:
                        condition:
                          service_healthy
                    healthcheck:
                      test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://opbeans-java:3000/"]
                      timeout: 5s
                      interval: 10s
                      retries: 36""")  # noqa: 501
        )

    def test_opbeans_java_image(self):
        opbeans = OpbeansJava(opbeans_java_image="foo").render()["opbeans-java"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_JAVA_IMAGE")]
        self.assertEqual(branch, ["OPBEANS_JAVA_IMAGE=foo"])

    def test_opbeans_java_no_infer_spans(self):
        opbeans = OpbeansJava(opbeans_java_no_infer_spans=True).render()["opbeans-java"]
        self.assertTrue("ELASTIC_APM_PROFILING_INFERRED_SPANS_ENABLED=true" not in opbeans['environment'])

    def opbeans_java_infer_spans_default_spans(self):
        opbeans = OpbeansJava().render()["opbeans-java"]
        self.assertTrue("ELASTIC_APM_PROFILING_INFERRED_SPANS_ENABLED=true" in opbeans['environment'])


    def test_opbeans_java_version(self):
        opbeans = OpbeansJava(opbeans_java_version="bar").render()["opbeans-java"]
        version = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_JAVA_VERSION")]
        self.assertEqual(version, ["OPBEANS_JAVA_VERSION=bar"])

    def test_opbeans_node(self):
        opbeans_node = OpbeansNode(version="6.2.4").render()
        self.assertEqual(
            opbeans_node, yaml.safe_load("""
                opbeans-node:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/node
                      args:
                      - OPBEANS_NODE_IMAGE=opbeans/opbeans-node
                      - OPBEANS_NODE_VERSION=latest
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
                        - ELASTIC_APM_JS_SERVER_URL=http://localhost:8200
                        - ELASTIC_APM_VERIFY_SERVER_CERT=true
                        - ELASTIC_APM_LOG_LEVEL=info
                        - ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5
                        - ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES
                        - WORKLOAD_ELASTIC_APM_APP_NAME=workload
                        - WORKLOAD_ELASTIC_APM_SERVER_URL=http://apm-server:8200
                        - WORKLOAD_DISABLED=False
                        - OPBEANS_SERVER_PORT=3000
                        - OPBEANS_SERVER_HOSTNAME=opbeans-node
                        - NODE_ENV=production
                        - PGHOST=postgres
                        - PGPASSWORD=verysecure
                        - PGPORT=5432
                        - PGUSER=postgres
                        - REDIS_URL=redis://redis:6379
                        - NODE_AGENT_BRANCH=
                        - NODE_AGENT_REPO=
                        - OPBEANS_DT_PROBABILITY=0.50
                        - ELASTIC_APM_ENVIRONMENT=production
                        - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                    depends_on:
                        postgres:
                          condition:
                            service_healthy
                        redis:
                          condition:
                            service_healthy
                        apm-server:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "wget", "-T", "3", "-q", "--server-response", "-O", "/dev/null", "http://opbeans-node:3000/"]
                        interval: 10s
                        retries: 12
                    volumes:
                        - ./docker/opbeans/node/sourcemaps:/sourcemaps""")  # noqa: 501
        )

    def test_opbeans_node_image(self):
        opbeans = OpbeansNode(opbeans_node_image="foo").render()["opbeans-node"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_NODE_IMAGE")]
        self.assertEqual(branch, ["OPBEANS_NODE_IMAGE=foo"])

    def test_opbeans_python_version(self):
        opbeans = OpbeansNode(opbeans_node_version="bar").render()["opbeans-node"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_NODE_VERSION")]
        self.assertEqual(branch, ["OPBEANS_NODE_VERSION=bar"])

    def test_opbeans_node_without_loadgen(self):
        opbeans_node = OpbeansNode(no_opbeans_node_loadgen=True).render()["opbeans-node"]
        value = [e for e in opbeans_node["environment"] if e.startswith("WORKLOAD_DISABLED")]
        self.assertEqual(value, ["WORKLOAD_DISABLED=True"])

    def test_opbeans_python(self):
        opbeans_python = OpbeansPython(version="6.2.4").render()
        self.assertEqual(
            opbeans_python, yaml.safe_load("""
                opbeans-python:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/python
                      args:
                      - OPBEANS_PYTHON_IMAGE=opbeans/opbeans-python
                      - OPBEANS_PYTHON_VERSION=latest
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
                        - ELASTIC_APM_SERVICE_VERSION=9c2e41c8-fb2f-4b75-a89d-5089fb55fc64
                        - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                        - ELASTIC_APM_JS_SERVER_URL=http://localhost:8200
                        - ELASTIC_APM_VERIFY_SERVER_CERT=true
                        - ELASTIC_APM_FLUSH_INTERVAL=5
                        - ELASTIC_APM_TRANSACTION_MAX_SPANS=50
                        - ELASTIC_APM_SOURCE_LINES_ERROR_APP_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_APP_FRAMES=5
                        - ELASTIC_APM_SOURCE_LINES_ERROR_LIBRARY_FRAMES
                        - ELASTIC_APM_SOURCE_LINES_SPAN_LIBRARY_FRAMES
                        - REDIS_URL=redis://redis:6379
                        - ELASTICSEARCH_URL=http://elasticsearch:9200
                        - OPBEANS_USER=opbeans_user
                        - OPBEANS_PASS=changeme
                        - OPBEANS_SERVER_URL=http://opbeans-python:3000
                        - PYTHON_AGENT_BRANCH=
                        - PYTHON_AGENT_REPO=
                        - PYTHON_AGENT_VERSION
                        - OPBEANS_DT_PROBABILITY=0.50
                        - ELASTIC_APM_ENVIRONMENT=production
                        - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                    depends_on:
                        postgres:
                          condition:
                            service_healthy
                        redis:
                          condition:
                            service_healthy
                        apm-server:
                          condition:
                            service_healthy
                        elasticsearch:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://opbeans-python:3000/"]
                        timeout: 5s
                        interval: 10s
                        retries: 12
            """)  # noqa: 501
        )

    def test_opbeans_python_agent_branch(self):
        opbeans_python_6_1 = OpbeansPython(version="6.1", opbeans_python_agent_branch="1.x").render()["opbeans-python"]
        branch = [e for e in opbeans_python_6_1["environment"] if e.startswith("PYTHON_AGENT_BRANCH")]
        self.assertEqual(branch, ["PYTHON_AGENT_BRANCH=1.x"])

        opbeans_python_main = OpbeansPython(
            version="7.0.0-alpha1", opbeans_python_agent_branch="2.x").render()["opbeans-python"]
        branch = [e for e in opbeans_python_main["environment"] if e.startswith("PYTHON_AGENT_BRANCH")]
        self.assertEqual(branch, ["PYTHON_AGENT_BRANCH=2.x"])

    def test_opbeans_python_agent_repo(self):
        agent_repo_default = OpbeansPython().render()["opbeans-python"]
        branch = [e for e in agent_repo_default["environment"] if e.startswith("PYTHON_AGENT_REPO")]
        self.assertEqual(branch, ["PYTHON_AGENT_REPO="])

        agent_repo_override = OpbeansPython(opbeans_python_agent_repo="myrepo").render()["opbeans-python"]
        branch = [e for e in agent_repo_override["environment"] if e.startswith("PYTHON_AGENT_REPO")]
        self.assertEqual(branch, ["PYTHON_AGENT_REPO=myrepo"])

    def test_opbeans_python_agent_local_repo(self):
        agent_repo_default = OpbeansPython().render()["opbeans-python"]
        assert "volumes" not in agent_repo_default

        agent_repo_override = OpbeansPython(opbeans_python_agent_local_repo=".").render()["opbeans-python"]
        assert "volumes" in agent_repo_override, agent_repo_override

    def test_opbeans_python_image(self):
        opbeans = OpbeansPython(opbeans_python_image="foo").render()["opbeans-python"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_PYTHON_IMAGE")]
        self.assertEqual(branch, ["OPBEANS_PYTHON_IMAGE=foo"])

    def test_opbeans_python_version(self):
        opbeans = OpbeansPython(opbeans_python_version="bar").render()["opbeans-python"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_PYTHON_VERSION")]
        self.assertEqual(branch, ["OPBEANS_PYTHON_VERSION=bar"])

    def test_opbeans_ruby(self):
        opbeans_ruby = OpbeansRuby(version="6.3.10").render()
        self.assertEqual(
            opbeans_ruby, yaml.safe_load("""
                opbeans-ruby:
                    build:
                      dockerfile: Dockerfile
                      context: docker/opbeans/ruby
                      args:
                        - OPBEANS_RUBY_IMAGE=opbeans/opbeans-ruby
                        - OPBEANS_RUBY_VERSION=latest
                    container_name: localtesting_6.3.10_opbeans-ruby
                    ports:
                      - "127.0.0.1:3001:3000"
                    environment:
                      - ELASTIC_APM_SERVER_URL=http://apm-server:8200
                      - ELASTIC_APM_SERVICE_NAME=opbeans-ruby
                      - ELASTIC_APM_SERVICE_VERSION=9c2e41c8-fb2f-4b75-a89d-5089fb55fc64
                      - ELASTIC_APM_VERIFY_SERVER_CERT=true
                      - DATABASE_URL=postgres://postgres:verysecure@postgres/opbeans-ruby
                      - REDIS_URL=redis://redis:6379
                      - ELASTICSEARCH_URL=http://elasticsearch:9200
                      - OPBEANS_SERVER_URL=http://opbeans-ruby:3000
                      - RAILS_ENV=production
                      - RAILS_LOG_TO_STDOUT=1
                      - PORT=3000
                      - RUBY_AGENT_BRANCH=
                      - RUBY_AGENT_REPO=
                      - RUBY_AGENT_VERSION
                      - OPBEANS_DT_PROBABILITY=0.50
                      - ELASTIC_APM_ENVIRONMENT=production
                      - ELASTIC_APM_TRANSACTION_SAMPLE_RATE=0.10
                    logging:
                      driver: 'json-file'
                      options:
                          max-size: '2m'
                          max-file: '5'
                    depends_on:
                      postgres:
                        condition:
                          service_healthy
                      redis:
                        condition:
                          service_healthy
                      apm-server:
                        condition:
                          service_healthy
                      elasticsearch:
                        condition:
                          service_healthy
                    healthcheck:
                      test: ["CMD", "wget", "-T", "3", "-q", "--server-response", "-O", "/dev/null", "http://opbeans-ruby:3000/"]
                      interval: 10s
                      retries: 50""")  # noqa: 501
        )

    def test_opbeans_ruby_image(self):
        opbeans = OpbeansRuby(opbeans_ruby_image="foo").render()["opbeans-ruby"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_RUBY_IMAGE")]
        self.assertEqual(branch, ["OPBEANS_RUBY_IMAGE=foo"])

    def test_opbeans_ruby_version(self):
        opbeans = OpbeansRuby(opbeans_ruby_version="bar").render()["opbeans-ruby"]
        branch = [e for e in opbeans["build"]["args"] if e.startswith("OPBEANS_RUBY_VERSION")]
        self.assertEqual(branch, ["OPBEANS_RUBY_VERSION=bar"])

    def test_opbeans_rum(self):
        opbeans_rum = OpbeansRum(version="6.3.10").render()
        self.assertEqual(
            opbeans_rum, yaml.safe_load("""
                opbeans-rum:
                     build:
                         dockerfile: Dockerfile
                         context: docker/opbeans/rum
                     container_name: localtesting_6.3.10_opbeans-rum
                     environment:
                         - OPBEANS_BASE_URL=http://opbeans-node:3000
                         - ELASTIC_APM_VERIFY_SERVER_CERT=true
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
                          condition:
                            service_healthy
                     healthcheck:
                         test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://localhost:9222/"]
                         timeout: 5s
                         interval: 10s
                         retries: 12""")  # noqa: 501
        )

    def test_opbeans_elasticsearch_urls(self):
        def assertOneElasticsearch(opbean):
            self.assertTrue("elasticsearch" in opbean['depends_on'])
            self.assertTrue("ELASTICSEARCH_URL=elasticsearch01:9200" in opbean['environment'])

        def assertTwoElasticsearch(opbean):
            self.assertTrue("elasticsearch" in opbean['depends_on'])
            self.assertTrue("ELASTICSEARCH_URL=elasticsearch01:9200,elasticsearch02:9200" in opbean['environment'])

        opbeans = OpbeansDotnet(opbeans_elasticsearch_urls=["elasticsearch01:9200"]).render()["opbeans-dotnet"]
        assertOneElasticsearch(opbeans)
        opbeans = OpbeansDotnet(opbeans_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                                ).render()["opbeans-dotnet"]
        assertTwoElasticsearch(opbeans)

        opbeans = OpbeansGo(opbeans_elasticsearch_urls=["elasticsearch01:9200"]).render()["opbeans-go"]
        assertOneElasticsearch(opbeans)
        opbeans = OpbeansGo(opbeans_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                            ).render()["opbeans-go"]
        assertTwoElasticsearch(opbeans)

        opbeans = OpbeansJava(opbeans_elasticsearch_urls=["elasticsearch01:9200"]).render()["opbeans-java"]
        assertOneElasticsearch(opbeans)
        opbeans = OpbeansJava(opbeans_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                              ).render()["opbeans-java"]
        assertTwoElasticsearch(opbeans)

        opbeans = OpbeansPython(opbeans_elasticsearch_urls=["elasticsearch01:9200"]).render()["opbeans-python"]
        assertOneElasticsearch(opbeans)
        opbeans = OpbeansPython(opbeans_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                                ).render()["opbeans-python"]
        assertTwoElasticsearch(opbeans)

        opbeans = OpbeansRuby(opbeans_elasticsearch_urls=["elasticsearch01:9200"]).render()["opbeans-ruby"]
        assertOneElasticsearch(opbeans)
        opbeans = OpbeansRuby(opbeans_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                              ).render()["opbeans-ruby"]
        assertTwoElasticsearch(opbeans)

    def test_opbeans_service_environment(self):
        def assertWithoutOption(opbean):
            self.assertTrue("ELASTIC_APM_ENVIRONMENT=production" in opbean['environment'])

        def assertWithOption(opbean):
            self.assertTrue("ELASTIC_APM_ENVIRONMENT=test" in opbean['environment'])

        opbeans = OpbeansDotnet().render()["opbeans-dotnet"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansDotnet(opbeans_dotnet_service_environment="test").render()["opbeans-dotnet"]
        assertWithOption(opbeans)

        opbeans = OpbeansGo().render()["opbeans-go"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansGo(opbeans_go_service_environment="test").render()["opbeans-go"]
        assertWithOption(opbeans)

        opbeans = OpbeansJava().render()["opbeans-java"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansJava(opbeans_java_service_environment="test").render()["opbeans-java"]
        assertWithOption(opbeans)

        opbeans = OpbeansPython().render()["opbeans-python"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansPython(opbeans_python_service_environment="test").render()["opbeans-python"]
        assertWithOption(opbeans)

        opbeans = OpbeansRuby().render()["opbeans-ruby"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansRuby(opbeans_ruby_service_environment="test").render()["opbeans-ruby"]
        assertWithOption(opbeans)

        opbeans = OpbeansNode().render()["opbeans-node"]
        assertWithoutOption(opbeans)
        opbeans = OpbeansNode(opbeans_node_service_environment="test").render()["opbeans-node"]
        assertWithOption(opbeans)

    def test_opbeans_secret_token(self):
        for cls in opbeans_services():
            services = cls(version="6.5.0", apm_server_secret_token="supersecret").render()
            opbeans_service = list(services.values())[0]
            secret_token = [e for e in opbeans_service["environment"] if e.startswith("ELASTIC_APM_SECRET_TOKEN=")]
            self.assertEqual(["ELASTIC_APM_SECRET_TOKEN=supersecret"], secret_token, cls.__name__)
        if cls is None:
            self.fail("no opbeans services tested")

    def test_opbeans_loadgen(self):
        opbeans_load_gen = OpbeansLoadGenerator(
            version="6.3.1",
            enable_opbeans_python=True,
            enable_opbeans_ruby=True,
            enable_opbeans_node=True,
            no_opbeans_node_loadgen=True,
            opbeans_python_loadgen_rpm=50,
            opbeans_ruby_loadgen_rpm=10,
        ).render()
        assert opbeans_load_gen == yaml.safe_load("""
            opbeans-load-generator:
                image: opbeans/opbeans-loadgen:latest
                container_name: localtesting_6.3.1_opbeans-load-generator
                depends_on:
                    opbeans-python:
                      condition:
                        service_healthy
                    opbeans-ruby:
                      condition:
                        service_healthy
                environment:
                 - 'WS=1'
                 - 'OPBEANS_URLS=opbeans-python:http://opbeans-python:3000,opbeans-ruby:http://opbeans-ruby:3000'
                 - 'OPBEANS_RPMS=opbeans-python:50,opbeans-ruby:10'
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports:
                - '8999:8000'""")


class PostgresServiceTest(ServiceTest):
    def test_postgres(self):
        postgres = Postgres(version="6.2.4").render()
        self.assertEqual(
            postgres, yaml.safe_load("""
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
            redis, yaml.safe_load("""
                redis:
                    image: redis:4
                    container_name: localtesting_6.2.4_redis
                    command: "--save ''"
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
    common_setup_args = ["start", "--docker-compose-path", "-", "--no-apm-server-self-instrument"]

    def test_service_registry(self):
        registry = discover_services()
        self.assertIn(ApmServer, registry)

    def test_start_6_2_default(self):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'6.2': '6.2.10'}):
            setup = LocalSetup(argv=self.common_setup_args +
                               ["6.2", "--image-cache-dir", image_cache_dir, "--no-xpack-secure"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        want = yaml.safe_load("""
        version: '2.4'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true,
                    -E, xpack.monitoring.enabled=true,
                    -E, 'apm-server.rum.allow_headers=["x-custom-header"]',
                    -E, setup.dashboards.enabled=true,
                    -E, 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', -E, output.elasticsearch.enabled=true]
                container_name: localtesting_6.2.10_apm-server
                depends_on:
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                environment: [
                    BEAT_STRICT_PERMS=false
                ]
                healthcheck:
                    interval: 10s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://localhost:8200/healthcheck']
                    timeout: 5s
                image: docker.elastic.co/apm/apm-server:6.2.10-SNAPSHOT
                labels: [co.elastic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060']

            elasticsearch:
                container_name: localtesting_6.2.10_elasticsearch
                environment: [bootstrap.memory_lock=true, cluster.name=docker-cluster, cluster.routing.allocation.disk.threshold_enabled=false, discovery.type=single-node, path.repo=/usr/share/elasticsearch/data/backups, 'ES_JAVA_OPTS=-Xms1g -Xmx1g', path.data=/usr/share/elasticsearch/data/6.2.10, xpack.security.enabled=false, xpack.license.self_generated.type=trial]
                healthcheck:
                    interval: 20s
                    retries: 10
                    test: [CMD-SHELL, 'curl -s -k http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch-platinum:6.2.10-SNAPSHOT
                labels: [co.elastic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: ['esdata:/usr/share/elasticsearch/data']

            kibana:
                container_name: localtesting_6.2.10_kibana
                depends_on:
                    elasticsearch: {condition: service_healthy}
                environment: {ELASTICSEARCH_HOSTS: 'http://elasticsearch:9200', SERVER_HOST: 0.0.0.0, SERVER_NAME: kibana.example.org, XPACK_FLEET_REGISTRYURL: 'https://epr-snapshot.elastic.co', XPACK_MONITORING_ENABLED: 'true'}
                healthcheck:
                    interval: 10s
                    retries: 30
                    start_period: 10s
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://kibana:5601/api/status']
                    timeout: 5s
                image: docker.elastic.co/kibana/kibana-x-pack:6.2.10-SNAPSHOT
                labels: [co.elastic.apm.stack-version=6.2.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
            wait-service:
                container_name: wait
                depends_on:
                    apm-server:
                        condition:
                            service_healthy
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                image: busybox
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
            setup = LocalSetup(argv=self.common_setup_args +
                               ["6.3", "--image-cache-dir", image_cache_dir, "--no-xpack-secure"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        want = yaml.safe_load("""
        version: '2.4'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.frontend.enabled=true, -E, apm-server.frontend.rate_limit=100000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, xpack.monitoring.elasticsearch=true, -E, xpack.monitoring.enabled=true,
                    -E, 'apm-server.rum.allow_headers=["x-custom-header"]',
                    -E, setup.dashboards.enabled=true,
                    -E, 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', -E, output.elasticsearch.enabled=true ]
                container_name: localtesting_6.3.10_apm-server
                depends_on:
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                environment: [
                    BEAT_STRICT_PERMS=false
                ]
                healthcheck:
                    interval: 10s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://localhost:8200/healthcheck']
                    timeout: 5s
                image: docker.elastic.co/apm/apm-server:6.3.10-SNAPSHOT
                labels: [co.elastic.apm.stack-version=6.3.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060']

            elasticsearch:
                container_name: localtesting_6.3.10_elasticsearch
                environment: [bootstrap.memory_lock=true, cluster.name=docker-cluster, cluster.routing.allocation.disk.threshold_enabled=false, discovery.type=single-node, path.repo=/usr/share/elasticsearch/data/backups, 'ES_JAVA_OPTS=-Xms1g -Xmx1g', path.data=/usr/share/elasticsearch/data/6.3.10, xpack.security.enabled=false, xpack.license.self_generated.type=trial, xpack.monitoring.collection.enabled=true]
                healthcheck:
                    interval: 20s
                    retries: 10
                    test: [CMD-SHELL, 'curl -s -k http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch:6.3.10-SNAPSHOT
                labels:
                    - co.elastic.apm.stack-version=6.3.10
                    - co.elastic.metrics/module=elasticsearch
                    - co.elastic.metrics/metricsets=node,node_stats
                    - co.elastic.metrics/hosts=http://$${data.host}:9200
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: ['esdata:/usr/share/elasticsearch/data']

            kibana:
                container_name: localtesting_6.3.10_kibana
                depends_on:
                    elasticsearch: {condition: service_healthy}
                environment: {ELASTICSEARCH_HOSTS: 'http://elasticsearch:9200', SERVER_HOST: 0.0.0.0, SERVER_NAME: kibana.example.org, XPACK_FLEET_REGISTRYURL: 'https://epr-snapshot.elastic.co', XPACK_MONITORING_ENABLED: 'true', XPACK_XPACK_MAIN_TELEMETRY_ENABLED: 'false'}
                healthcheck:
                    interval: 10s
                    retries: 30
                    start_period: 10s
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://kibana:5601/api/status']
                    timeout: 5s
                image: docker.elastic.co/kibana/kibana:6.3.10-SNAPSHOT
                labels: [co.elastic.apm.stack-version=6.3.10]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
            wait-service:
                container_name: wait
                depends_on:
                    apm-server:
                        condition:
                            service_healthy
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                image: busybox
        networks:
            default: {name: apm-integration-testing}
        volumes:
            esdata: {driver: local}
            pgdata: {driver: local}
        """)  # noqa: 501
        self.assertDictEqual(got, want)

    def test_version_options(self):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-java",
                                                              "--image-cache-dir", image_cache_dir, "--opbeans-java-service-version", "1.2.3"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        self.assertIn('ELASTIC_APM_SERVICE_VERSION=1.2.3', got['services']['opbeans-java']['environment'])

    def test_start_master_default(self):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--image-cache-dir", image_cache_dir])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        want = yaml.safe_load("""
        version: '2.4'
        services:
            apm-server:
                cap_add: [CHOWN, DAC_OVERRIDE, SETGID, SETUID]
                cap_drop: [ALL]
                command: [apm-server, -e, --httpprof, ':6060', -E, apm-server.rum.enabled=true, -E, apm-server.rum.event_rate.limit=1000,
                    -E, 'apm-server.host=0.0.0.0:8200', -E, apm-server.read_timeout=1m, -E, apm-server.shutdown_timeout=2m,
                    -E, apm-server.write_timeout=1m, -E, logging.json=true, -E, logging.metrics.enabled=false,
                    -E, setup.template.settings.index.number_of_replicas=0,
                    -E, setup.template.settings.index.number_of_shards=1, -E, setup.template.settings.index.refresh_interval=1ms,
                    -E, monitoring.elasticsearch=true, -E, monitoring.enabled=true,
                    -E, 'apm-server.rum.allow_headers=["x-custom-header"]',
                    -E, apm-server.mode=experimental,
                    -E, apm-server.kibana.enabled=true, -E, 'apm-server.kibana.host=kibana:5601', -E, apm-server.agent.config.cache.expiration=30s,
                    -E, apm-server.kibana.username=apm_server_user, -E, apm-server.kibana.password=changeme,
                    -E, apm-server.jaeger.http.enabled=true, -E, "apm-server.jaeger.http.host=0.0.0.0:14268",
                    -E, apm-server.jaeger.grpc.enabled=true, -E, "apm-server.jaeger.grpc.host=0.0.0.0:14250",
                    -E, apm-server.sampling.keep_unsampled=true,
                    -E, 'output.elasticsearch.hosts=["http://elasticsearch:9200"]',
                    -E, output.elasticsearch.username=apm_server_user, -E, output.elasticsearch.password=changeme,
                    -E, output.elasticsearch.enabled=true,
                    -E, "output.elasticsearch.pipelines=[{pipeline: 'apm'}]", -E, 'apm-server.register.ingest.pipeline.enabled=true'
                    ]
                container_name: localtesting_8.0.0_apm-server
                depends_on:
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                environment: [
                    BEAT_STRICT_PERMS=false
                ]
                healthcheck:
                    interval: 10s
                    retries: 12
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://localhost:8200/']
                    timeout: 5s
                image: docker.elastic.co/apm/apm-server:8.0.0-SNAPSHOT
                labels: [co.elastic.apm.stack-version=8.0.0]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:8200:8200', '127.0.0.1:6060:6060', '127.0.0.1:14268:14268', '127.0.0.1:14250:14250']

            elasticsearch:
                container_name: localtesting_8.0.0_elasticsearch
                environment: [
                    bootstrap.memory_lock=true,
                    cluster.name=docker-cluster,
                    cluster.routing.allocation.disk.threshold_enabled=false,
                    discovery.type=single-node,
                    path.repo=/usr/share/elasticsearch/data/backups,
                    'ES_JAVA_OPTS=-XX:UseAVX=2 -Xms1g -Xmx1g',
                    path.data=/usr/share/elasticsearch/data/8.0.0,
                    indices.id_field_data.enabled=true,
                    action.destructive_requires_name=false,
                    xpack.security.authc.anonymous.roles=remote_monitoring_collector,
                    xpack.security.authc.realms.file.file1.order=0,
                    xpack.security.authc.realms.native.native1.order=1,
                    xpack.security.authc.token.enabled=true,
                    xpack.security.authc.api_key.enabled=true,
                    xpack.security.enabled=true,
                    xpack.license.self_generated.type=trial,
                    xpack.monitoring.collection.enabled=true
                ]
                healthcheck:
                    interval: 20s
                    retries: 10
                    test: [CMD-SHELL, 'curl -s -k http://localhost:9200/_cluster/health | grep -vq ''"status":"red"''']
                image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0-SNAPSHOT
                labels:
                    - co.elastic.apm.stack-version=8.0.0
                    - co.elastic.metrics/module=elasticsearch
                    - co.elastic.metrics/metricsets=node,node_stats
                    - co.elastic.metrics/hosts=http://$${data.host}:9200
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:9200:9200']
                ulimits:
                    memlock: {hard: -1, soft: -1}
                volumes: [
                    'esdata:/usr/share/elasticsearch/data',
                    './docker/elasticsearch/roles.yml:/usr/share/elasticsearch/config/roles.yml',
                    './docker/elasticsearch/users:/usr/share/elasticsearch/config/users',
                    './docker/elasticsearch/users_roles:/usr/share/elasticsearch/config/users_roles'
                ]

            kibana:
                container_name: localtesting_8.0.0_kibana
                depends_on:
                    elasticsearch:
                        condition:
                            service_healthy
                environment: {
                    ELASTICSEARCH_PASSWORD: changeme,
                    ELASTICSEARCH_HOSTS: 'http://elasticsearch:9200',
                    ELASTICSEARCH_USERNAME: kibana_system_user,
                    ENTERPRISESEARCH_HOST: 'http://enterprise-search:3002',
                    SERVER_HOST: 0.0.0.0,
                    SERVER_NAME: kibana.example.org,
                    STATUS_ALLOWANONYMOUS: 'true',
                    TELEMETRY_ENABLED: 'false',
                    XPACK_APM_SERVICEMAPENABLED: 'true',
                    XPACK_MONITORING_ENABLED: 'true',
                    XPACK_REPORTING_ROLES_ENABLED: 'false',
                    XPACK_SECURITY_ENCRYPTIONKEY: 'fhjskloppd678ehkdfdlliverpoolfcr',
                    XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY: 'fhjskloppd678ehkdfdlliverpoolfcr',
                    XPACK_FLEET_AGENTS_ELASTICSEARCH_HOSTS: '["http://elasticsearch:9200"]',
                    XPACK_FLEET_REGISTRYURL: 'https://epr-snapshot.elastic.co',
                    XPACK_XPACK_MAIN_TELEMETRY_ENABLED: 'false',
                    XPACK_SECURITY_LOGINASSISTANCEMESSAGE: 'Login&#32;details:&#32;`admin/changeme`.&#32;Further&#32;details&#32;[here](https://github.com/elastic/apm-integration-testing#logging-in).',
                    XPACK_SECURITY_SESSION_IDLETIMEOUT: '1M',
                    XPACK_SECURITY_SESSION_LIFESPAN: '3M',
                }
                healthcheck:
                    interval: 10s
                    retries: 30
                    start_period: 10s
                    test: [CMD, curl, --write-out, '''HTTP %{http_code}''', -k, --fail, --silent, --output, /dev/null, 'http://kibana:5601/api/status']
                    timeout: 5s
                image: docker.elastic.co/kibana/kibana:8.0.0-SNAPSHOT
                labels: [co.elastic.apm.stack-version=8.0.0]
                logging:
                    driver: json-file
                    options: {max-file: '5', max-size: 2m}
                ports: ['127.0.0.1:5601:5601']
            wait-service:
                container_name: wait
                depends_on:
                    apm-server:
                        condition:
                            service_healthy
                    elasticsearch:
                        condition:
                            service_healthy
                    kibana:
                        condition:
                            service_healthy
                image: busybox
        networks:
            default: {name: apm-integration-testing}
        volumes:
            esdata: {driver: local}
            pgdata: {driver: local}
        """)  # noqa: 501
        self.assertDictEqual(got, want)

    def test_start_master_with_oss(self):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            with self.assertRaises(SystemExit) as cm:
                setup = LocalSetup(argv=self.common_setup_args +
                                   ["master", "--image-cache-dir", image_cache_dir, "--oss"])
                setup.set_docker_compose_path(docker_compose_yml)
                setup()
            self.assertEqual(cm.exception.code, 1)

    def test_start_master_with_apm_oss(self):
        docker_compose_yml = stringIO()
        version = "8.0.0"
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': version}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--apm-server-oss"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch:{}-SNAPSHOT".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana:{}-SNAPSHOT".format(version), services["kibana"]["image"])
        self.assertEqual("docker.elastic.co/apm/apm-server-oss:{}-SNAPSHOT".format(version),
                         services["apm-server"]["image"])

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_6_x_xpack_secure(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'6.6': '6.6.10'}):
            setup = LocalSetup(argv=self.common_setup_args + ["6.6", "--elasticsearch-xpack-audit"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        # apm-server should use user/pass -> es
        apm_server_cmd = got["services"]["apm-server"]["command"]
        self.assertTrue(any(cmd.startswith("output.elasticsearch.password=") for cmd in apm_server_cmd), apm_server_cmd)
        self.assertTrue(any(cmd.startswith("output.elasticsearch.username=") for cmd in apm_server_cmd), apm_server_cmd)
        self.assertFalse(any(cmd == "setup.dashboards.enabled=true" for cmd in apm_server_cmd), apm_server_cmd)
        # elasticsearch configuration
        es_env = got["services"]["elasticsearch"]["environment"]
        # auditing enabled
        self.assertIn("xpack.security.audit.enabled=true", es_env)
        # allow anonymous healthcheck
        self.assertIn("xpack.security.authc.anonymous.roles=remote_monitoring_collector", es_env)
        # file based realm
        self.assertIn("xpack.security.authc.realms.file1.type=file", es_env)
        # native realm
        self.assertIn("xpack.security.authc.realms.native1.type=native", es_env)
        # kibana should use user/pass -> es
        kibana_env = got["services"]["kibana"]["environment"]
        self.assertIn("ELASTICSEARCH_PASSWORD", kibana_env)
        self.assertIn("ELASTICSEARCH_USERNAME", kibana_env)
        # allow anonymous healthcheck
        self.assertIn("STATUS_ALLOWANONYMOUS", kibana_env)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_7_0_xpack_secure(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        # apm-server should use user/pass -> es
        apm_server_cmd = got["services"]["apm-server"]["command"]
        self.assertTrue(any(cmd.startswith("output.elasticsearch.password=") for cmd in apm_server_cmd), apm_server_cmd)
        self.assertTrue(any(cmd.startswith("output.elasticsearch.username=") for cmd in apm_server_cmd), apm_server_cmd)
        # elasticsearch configuration
        es_env = got["services"]["elasticsearch"]["environment"]
        # auditing disabled by default
        self.assertNotIn("xpack.security.audit.enabled=true", es_env)
        # allow anonymous healthcheck
        self.assertIn("xpack.security.authc.anonymous.roles=remote_monitoring_collector", es_env)
        # file based realm
        self.assertIn("xpack.security.authc.realms.file.file1.order=0", es_env)
        # native realm
        self.assertIn("xpack.security.authc.realms.native.native1.order=1", es_env)
        # kibana should use user/pass -> es
        kibana_env = got["services"]["kibana"]["environment"]
        self.assertIn("ELASTICSEARCH_PASSWORD", kibana_env)
        self.assertIn("ELASTICSEARCH_USERNAME", kibana_env)
        # allow anonymous healthcheck
        self.assertIn("STATUS_ALLOWANONYMOUS", kibana_env)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_no_elasticesarch(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--no-elasticsearch"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertNotIn("elasticsearch", services)
        self.assertNotIn("elasticsearch", services["apm-server"]["depends_on"])

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_all(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertSetEqual(services, {
            "apm-server", "elasticsearch", "kibana",
            "filebeat", "heartbeat", "metricbeat", "packetbeat",
            "opbeans-dotnet",
            "opbeans-go",
            "opbeans-java",
            "opbeans-load-generator",
            "opbeans-node",
            "opbeans-python",
            "opbeans-ruby",
            "opbeans-rum",
            "postgres",
            "redis",
            "wait-service",
        })

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_one_opbeans(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-python"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertIn("redis", services)
        self.assertIn("postgres", services)
        self.assertIn("opbeans-load-generator", services)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_one_opbeans_without_loadgen(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-python",
                                                              "--no-opbeans-python-loadgen"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertIn("redis", services)
        self.assertIn("postgres", services)
        self.assertNotIn("opbeans-load-generator", services)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_one_opbeans_without_loadgen_global_arg(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-python",
                                                              "--no-opbeans-load-generator"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertIn("redis", services)
        self.assertIn("postgres", services)
        self.assertNotIn("opbeans-load-generator", services)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_opbeans_2nd(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-dotnet01", "--with-opbeans-node01",
                                                              "--with-opbeans-java01", "--with-opbeans-go01",
                                                              "--with-opbeans-python01", "--with-opbeans-ruby01"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertIn("opbeans-dotnet01", services)
        self.assertIn("opbeans-node01", services)
        self.assertIn("opbeans-java01", services)
        self.assertIn("opbeans-go01", services)
        self.assertIn("opbeans-python01", services)
        self.assertIn("opbeans-ruby01", services)

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_all_opbeans_no_apm_server(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all-opbeans", "--no-apm-server"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        depends_on = set(got["services"]["opbeans-node"]["depends_on"])
        self.assertSetEqual({"postgres", "redis"}, depends_on)
        depends_on = set(got["services"]["opbeans-python"]["depends_on"])
        self.assertSetEqual({"elasticsearch", "postgres", "redis"}, depends_on)
        depends_on = set(got["services"]["opbeans-ruby"]["depends_on"])
        self.assertSetEqual({"elasticsearch", "postgres", "redis"}, depends_on)
        for name, service in got["services"].items():
            self.assertNotIn("apm-server", service.get("depends_on", []), "{} depends on apm-server".format(name))

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_unsupported_version_pre_6_3(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        version = "1.2.3"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(argv=self.common_setup_args + [version, "--release"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch-platinum:{}".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana-x-pack:{}".format(version), services["kibana"]["image"])

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_unsupported_version(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        version = "6.9.5"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(argv=self.common_setup_args + [version])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch:{}-SNAPSHOT".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana:{}-SNAPSHOT".format(version), services["kibana"]["image"])

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_with_dyno(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains a configuration block for the Dyno container
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        self.assertIn('dyno', got['services'])

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_with_dyno_defaults(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains the defaults for Dyno
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        received = yaml.safe_load(docker_compose_yml)
        got = received['services']['dyno']
        want = {
            'build':
                {
                    'args': [],
                    'context': 'docker/dyno',
                    'dockerfile': 'Dockerfile'
                },
            'container_name': 'dyno',
                'environment': {'TOXI_HOST': 'toxi', 'TOXI_PORT': '8474'},
                'healthcheck': {
                    'interval': '10s',
                    'retries': 12,
                    'test': [
                        'CMD',
                        'wget',
                        '-T',
                        '3',
                        '-q',
                        '--server-response',
                        '-O',
                        '/dev/null',
                        'http://localhost:8000/'
                    ]
                },
                'ports': ['9000:8000'],
                'volumes': [
                    '/var/run/docker.sock:/var/run/docker.sock',
                    './docker/dyno:/dyno'
                ]}
        self.assertDictEqual(got, want)

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_with_toxi(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains a configuration block for the Toxi container
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        self.assertIn('toxi', got['services'])

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_toxi_docker_defaults(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains a configuration block for the Toxi container
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        received = yaml.safe_load(docker_compose_yml)
        got = received['services']['toxi']
        want = {
            'command': [
                '-host=0.0.0.0',
                '-config=/toxi/toxi.cfg'
            ],
            'container_name': 'localtesting_8.0_toxi',
            'healthcheck': {
                'interval': '10s',
                'retries': 12,
                'test': [
                    'CMD',
                    'wget',
                    '-T',
                    '3',
                    '-q',
                    '--server-response',
                    '-O',
                    '/dev/null',
                    'http://localhost:8474/proxies'
                ]
            },
            'image': 'shopify/toxiproxy',
            'logging': {
                'driver': 'json-file',
                'options': {
                    'max-file': '5',
                    'max-size': '2m'
                }
            },
            'ports': [
                '8474:8474',
                '3004:3004',
                '3003:3003',
                '3002:3002',
                '3000:3000',
                '8000:8000',
                '3001:3001'
            ],
            'restart': 'on-failure',
            'volumes': [
                './docker/toxi/toxi.cfg:/toxi/toxi.cfg'
            ]
        }
        self.assertDictEqual(got, want)

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_dyno_implies_statsd(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains a configuration block for the StatsD container
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        self.assertIn('stats-d', got['services'])

    @mock.patch(cli.__name__ + ".load_images")
    @mock.patch(cli.__name__ + ".open")
    def test_start_dyno_generates_statsd_config(self, _ignore_load_images, _ignore_open):
        """
        GIVEN a mocked CLI which does not actually load images
        WHEN the CLI is called with the --dyno flag
        THEN the generated Docker Compose file contains the correct configuration for StatsD
        """
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        want = {
            'build': {
                'args': [],
                'context': 'docker/statsd',
                'dockerfile': 'Dockerfile'
            },
            'container_name': 'localtesting_8.0_stats-d',
            'healthcheck': {
                'interval': '10s',
                'test': ['CMD', 'pidof', 'node']
            },
            'logging': {
                'driver': 'json-file',
                'options': {'max-file': '5', 'max-size': '2m'}
            },
            'ports': [
                '8125:8125/udp',
                '8126:8126',
                '8127:8127'
            ]
        }

    @mock.patch(cli.__name__ + ".load_images")
    def test_start_with_toxi_cfg(self, _ignore_load_images):
        """
        GIVEN a mocked CLI which does not actually write a config
        WHEN the CLI is called with the --dyno flag
        THEN the generated toxi.cfg would contain the correct defaults
        """
        docker_compose_yml = stringIO()
        toxi_open = mock.mock_open()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            with mock.patch('scripts.modules.cli.open', toxi_open):
                setup = LocalSetup(argv=self.common_setup_args + ["master", "--all", "--dyno"])
                setup.set_docker_compose_path(docker_compose_yml)
                setup()
        want = '[\n    {\n        "enabled": true,\n        "listen": "[::]:3004",\n        "name": "opbeans-dotnet",\n        "upstream": "opbeans-dotnet:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:3003",\n        "name": "opbeans-go",\n        "upstream": "opbeans-go:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:3002",\n        "name": "opbeans-java",\n        "upstream": "opbeans-java:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:3000",\n        "name": "opbeans-node",\n        "upstream": "opbeans-node:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:8000",\n        "name": "opbeans-python",\n        "upstream": "opbeans-python:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:3001",\n        "name": "opbeans-ruby",\n        "upstream": "opbeans-ruby:3000"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:5432",\n        "name": "postgres",\n        "upstream": "postgres:5432"\n    },\n    {\n        "enabled": true,\n        "listen": "[::]:6379",\n        "name": "redis",\n        "upstream": "redis:6379"\n    }\n]'
        toxi_open().write.assert_called_once_with(want)

    @mock.patch(service.__name__ + ".resolve_bc")
    @mock.patch(cli.__name__ + ".load_images")
    def test_start_bc(self, mock_load_images, mock_resolve_bc):
        mock_resolve_bc.return_value = {
            "projects": {
                "elasticsearch": {
                    "packages": {
                        "elasticsearch-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "kibana": {
                    "packages": {
                        "kibana-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../kibana-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "apm-server": {
                    "packages": {
                        "apm-server-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../apm-server-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "beats": {
                    "packages": {
                        "metricbeat-6.9.5-linux-amd64-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../metricbeat-6.9.5-docker-image.tar.gz",
                            "type": "docker",
                        },
                    }
                },
                "logstash-docker": {
                    "packages": {
                        "logstash-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../logstash-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
            },
        }
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        version = "6.9.5"
        bc = "abcd1234"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(argv=self.common_setup_args + [
            version, "--bc", bc, "--image-cache-dir", image_cache_dir, "--with-logstash", "--with-metricbeat"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch:{}".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana:{}".format(version), services["kibana"]["image"])
        mock_load_images.assert_called_once_with(
            {
                "https://staging.elastic.co/.../elasticsearch-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../logstash-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../kibana-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../apm-server-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../metricbeat-6.9.5-docker-image.tar.gz",
            },
            image_cache_dir)

    @mock.patch(service.__name__ + ".resolve_bc")
    @mock.patch(cli.__name__ + ".load_images")
    def test_start_bc_oss(self, mock_load_images, mock_resolve_bc):
        mock_resolve_bc.return_value = {
            "projects": {
                "elasticsearch": {
                    "packages": {
                        "elasticsearch-oss-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-oss-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "kibana": {
                    "packages": {
                        "kibana-oss-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../kibana-oss-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "apm-server": {
                    "packages": {
                        "apm-server-oss-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../apm-server-oss-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
            },
        }
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        version = "6.9.5"
        bc = "abcd1234"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(argv=self.common_setup_args + [
            version, "--oss",  "--bc", bc, "--image-cache-dir", image_cache_dir])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch-oss:{}".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana-oss:{}".format(version), services["kibana"]["image"])
        mock_load_images.assert_called_once_with(
            {
                "https://staging.elastic.co/.../elasticsearch-oss-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../kibana-oss-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../apm-server-oss-6.9.5-docker-image.tar.gz",
            },
            image_cache_dir)

    @mock.patch(service.__name__ + ".resolve_bc")
    @mock.patch(cli.__name__ + ".load_images")
    def test_start_bc_with_release(self, mock_load_images, mock_resolve_bc):
        mock_resolve_bc.return_value = {
            "projects": {
                "elasticsearch": {
                    "packages": {
                        "elasticsearch-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "kibana": {
                    "packages": {
                        "kibana-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../kibana-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "apm-server": {
                    "packages": {
                        "apm-server-6.9.5-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../apm-server-6.9.5-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
            },
        }
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        version = "6.9.5"
        apm_server_version = "6.2.4"
        bc = "abcd1234"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(
            argv=self.common_setup_args + [version, "--bc", bc, "--image-cache-dir", image_cache_dir,
                                           "--apm-server-version", apm_server_version, "--apm-server-release"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/apm/apm-server:{}".format(apm_server_version),
            services["apm-server"]["image"]
        )
        mock_load_images.assert_called_once_with(
            {
                "https://staging.elastic.co/.../elasticsearch-6.9.5-docker-image.tar.gz",
                "https://staging.elastic.co/.../kibana-6.9.5-docker-image.tar.gz",
            },
            image_cache_dir)

    @mock.patch(service.__name__ + ".resolve_bc")
    @mock.patch(cli.__name__ + ".load_images")
    def test_start_bc_ubi8(self, mock_load_images, mock_resolve_bc):
        mock_resolve_bc.return_value = {
            "projects": {
                "elasticsearch": {
                    "packages": {
                        "elasticsearch-ubi8-7.10.0-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-ubi8-7.10.0-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "kibana": {
                    "packages": {
                        "kibana-ubi8-7.10.0-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../kibana-ubi8-7.10.0-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
                "apm-server": {
                    "packages": {
                        "apm-server-ubi8-7.10.0-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../apm-server-ubi8-7.10.0-docker-image.tar.gz",
                            "type": "docker"
                        },
                    },
                },
            },
        }
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        version = "7.10.0"
        bc = "abcd1234"
        self.assertNotIn(version, LocalSetup.SUPPORTED_VERSIONS)
        setup = LocalSetup(argv=self.common_setup_args + [
            version, "--ubi8",  "--bc", bc, "--image-cache-dir", image_cache_dir])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = got["services"]
        self.assertEqual(
            "docker.elastic.co/elasticsearch/elasticsearch-ubi8:{}".format(version),
            services["elasticsearch"]["image"]
        )
        self.assertEqual("docker.elastic.co/kibana/kibana-ubi8:{}".format(version), services["kibana"]["image"])
        mock_load_images.assert_called_once_with(
            {
                "https://staging.elastic.co/.../elasticsearch-ubi8-7.10.0-docker-image.tar.gz",
                "https://staging.elastic.co/.../kibana-ubi8-7.10.0-docker-image.tar.gz",
                "https://staging.elastic.co/.../apm-server-ubi8-7.10.0-docker-image.tar.gz",
            },
            image_cache_dir)

    @mock.patch(service.__name__ + ".resolve_bc")
    def test_docker_download_image_url(self, mock_resolve_bc):
        mock_resolve_bc.return_value = {
            "projects": {
                "elasticsearch": {
                    "commit_hash": "abc1234",
                    "commit_url": "https://github.com/elastic/elasticsearch/commits/abc1234",
                    "packages": {
                        "elasticsearch-6.3.10-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-6.3.10-docker-image.tar.gz",
                            "type": "docker"
                        },
                        "elasticsearch-oss-6.3.10-docker-image.tar.gz": {
                            "url": "https://staging.elastic.co/.../elasticsearch-oss-6.3.10-docker-image.tar.gz",
                            "type": "docker"
                        }
                    }
                }
            }
        }
        Case = collections.namedtuple("Case", ("service", "expected", "args"))
        common_args = (("image_cache_dir", ".images"),)
        cases = [
            # post-6.3
            Case(Elasticsearch,
                 "https://staging.elastic.co/.../elasticsearch-6.3.10-docker-image.tar.gz",
                 dict(bc="be84d930", version="6.3.10")),
            Case(Elasticsearch,
                 "https://staging.elastic.co/.../elasticsearch-oss-6.3.10-docker-image.tar.gz",
                 dict(bc="be84d930", oss=True, version="6.3.10")),
        ]
        for case in cases:
            args = dict(common_args)
            if case.args:
                args.update(case.args)
            service = case.service(**args)
            got = service.image_download_url()
            self.assertEqual(case.expected, got)

    @mock.patch(cli.__name__ + ".load_images")
    def test_apm_server_tls(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--with-opbeans-python",
                                                              "--apm-server-enable-tls"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertIn("apm-server", services)
        self.assertIn("opbeans-python", services)

        apm_server = got["services"]["apm-server"]
        self.assertIn("apm-server.ssl.enabled=true", apm_server["command"])
        self.assertIn("apm-server.ssl.key=/usr/share/apm-server/config/certs/tls.key", apm_server["command"])
        self.assertIn("apm-server.ssl.certificate=/usr/share/apm-server/config/certs/tls.crt", apm_server["command"])
        self.assertIn("https://localhost:8200/", apm_server["healthcheck"]["test"])

        opbeans_python = got["services"]["opbeans-python"]
        self.assertIn("ELASTIC_APM_SERVER_URL=https://apm-server:8200", opbeans_python["environment"])
        self.assertIn("ELASTIC_APM_JS_SERVER_URL=https://apm-server:8200", opbeans_python["environment"])

    def test_apm_server_kibana_url(self):
        apmServer = ApmServer(apm_server_kibana_url="http://kibana.example.com:5601").render()["apm-server"]
        self.assertIn("apm-server.kibana.host=http://kibana.example.com:5601", apmServer["command"])

    def test_apm_server_index_refresh_interval(self):
        apmServer = ApmServer(apm_server_index_refresh_interval="10ms").render()["apm-server"]
        self.assertIn("setup.template.settings.index.refresh_interval=10ms", apmServer["command"])

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

    @mock.patch(cli.__name__ + ".load_images")
    def test_elasticsearch_tls(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--elasticsearch-enable-tls"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertIn("elasticsearch", services)

        elasticsearch = got["services"]["elasticsearch"]
        certs = "/usr/share/elasticsearch/config/certs/tls.crt"
        certsKey = "/usr/share/elasticsearch/config/certs/tls.key"
        caCerts = "/usr/share/elasticsearch/config/certs/ca.crt"
        self.assertIn("xpack.security.http.ssl.enabled=true", elasticsearch["environment"])
        self.assertIn("xpack.security.transport.ssl.enabled=true", elasticsearch["environment"])
        self.assertIn("xpack.security.http.ssl.enabled=true", elasticsearch["environment"])
        self.assertIn("xpack.security.http.ssl.enabled=true", elasticsearch["environment"])
        self.assertIn("xpack.security.http.ssl.key=" + certsKey, elasticsearch["environment"])
        self.assertIn("xpack.security.http.ssl.certificate=" + certs, elasticsearch["environment"])
        self.assertIn("xpack.security.http.ssl.certificate_authorities=" + caCerts, elasticsearch["environment"])
        self.assertIn("xpack.security.transport.ssl.key=" + certsKey, elasticsearch["environment"])
        self.assertIn("xpack.security.transport.ssl.certificate=" + certs, elasticsearch["environment"])
        self.assertIn("xpack.security.transport.ssl.certificate_authorities=" + caCerts, elasticsearch["environment"])
        self.assertIn("curl -s -k https://localhost:9200/_cluster/health | grep -vq '\"status\":\"red\"'",
                      elasticsearch["healthcheck"]["test"])

    @mock.patch(cli.__name__ + ".load_images")
    def test_kibana_tls(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            setup = LocalSetup(argv=self.common_setup_args + ["master", "--kibana-enable-tls"])
            setup.set_docker_compose_path(docker_compose_yml)
            setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertIn("kibana", services)

        kibana = got["services"]["kibana"]
        certs = "/usr/share/kibana/config/certs/tls.crt"
        certsKey = "/usr/share/kibana/config/certs/tls.key"
        caCerts = "/usr/share/kibana/config/certs/ca.crt"
        self.assertIn("true", kibana["environment"]["SERVER_SSL_ENABLED"])
        self.assertIn(certs, kibana["environment"]["SERVER_SSL_CERTIFICATE"])
        self.assertIn(certsKey, kibana["environment"]["SERVER_SSL_KEY"])
        self.assertIn(caCerts, kibana["environment"]["ELASTICSEARCH_SSL_CERTIFICATEAUTHORITIES"])

    @mock.patch(cli.__name__ + ".load_images")
    def test_kibana_src(self, _ignore_load_images):
        docker_compose_yml = stringIO()
        with mock.patch.dict(LocalSetup.SUPPORTED_VERSIONS, {'master': '8.0.0'}):
            with mock.patch('builtins.open', mock.mock_open(read_data='14.17.3\n')):
                setup = LocalSetup(argv=self.common_setup_args + [
                    "master", "--kibana-src=/foo", "--kibana-src-start-cmd=bar"])
                setup.set_docker_compose_path(docker_compose_yml)
                setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertIn("kibana", services)

        kibana = got["services"]["kibana"]
        self.assertIn("/foo:/usr/share/kibana", kibana["volumes"])
        self.assertIn("bar", kibana["command"])
        self.assertIn("true", kibana["environment"]["BABEL_DISABLE_CACHE"])
        self.assertIn("--max-old-space-size=4096", kibana["environment"]["NODE_OPTIONS"])
        self.assertIn("/usr/share/kibana", kibana["environment"]["HOME"])
        self.assertIn("true", kibana["environment"]["BABEL_DISABLE_CACHE"])
        self.assertIn("NODE_VERSION=14.17.3", kibana["build"]["args"])
        self.assertIn("UID={}".format(os.getuid()), kibana["build"]["args"])
        self.assertIn("GID={}".format(os.getgid()), kibana["build"]["args"])

    def test_elasticsearch_snapshot_repo(self):
        docker_compose_yml = stringIO()
        image_cache_dir = "/foo"
        setup = LocalSetup(argv=self.common_setup_args + ["8.0.0", "--image-cache-dir", image_cache_dir,
                                                          "--elasticsearch-snapshot-repo", "https://example.com/1/",
                                                          "--elasticsearch-snapshot-repo", "https://example.com/2/"])
        setup.set_docker_compose_path(docker_compose_yml)
        setup()
        docker_compose_yml.seek(0)
        got = yaml.safe_load(docker_compose_yml)
        services = set(got["services"])
        self.assertIn("repo0", services)
        self.assertIn("repo1", services)
        repo0 = got["services"]["repo0"]
        self.assertIn('{"type": "url", "settings": {"url": "https://example.com/1/"}}', repo0["command"])
