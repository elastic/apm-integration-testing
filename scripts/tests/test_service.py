from __future__ import print_function

import json
import os
import unittest

import yaml

from ..modules.apm_agents import (
    AgentGoNetHttp, AgentNodejsExpress, AgentPythonDjango, AgentPythonFlask, AgentRubyRails,
    AgentJavaSpring, AgentDotnet, AgentPhpApache
)
from ..modules.aux_services import Logstash, Kafka, Zookeeper
from ..modules.beats import Filebeat, Heartbeat, Metricbeat, Packetbeat
from ..modules.elastic_stack import ApmServer, ElasticAgent, Elasticsearch, EnterpriseSearch, Kibana, PackageRegistry


class ServiceTest(unittest.TestCase):
    maxDiff = None


class AgentServiceTest(ServiceTest):
    def test_agent_go_net_http(self):
        agent = AgentGoNetHttp().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-go-net-http:
                    build:
                        args:
                            GO_AGENT_BRANCH: main
                            GO_AGENT_REPO: elastic/apm-agent-go
                        dockerfile: Dockerfile
                        context: docker/go/nethttp
                    container_name: gonethttpapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_FLUSH_INTERVAL: 500ms
                        ELASTIC_APM_LOG_LEVEL: 'info'
                        ELASTIC_APM_SERVICE_NAME: gonethttpapp
                        ELASTIC_APM_TRANSACTION_IGNORE_NAMES: healthcheck
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://gonethttpapp:8080/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8080:8080
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentGoNetHttp(apm_server_url="http://foo").render()["agent-go-net-http"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URL"], agent)

    def test_agent_go_with_repo(self):
        agent = AgentGoNetHttp(go_agent_repo="foo/myrepo.git").render()["agent-go-net-http"]
        self.assertEqual("foo/myrepo.git", agent["build"]["args"]["GO_AGENT_REPO"])

    def test_agent_go_with_version(self):
        agent = AgentGoNetHttp(go_agent_version="bar").render()["agent-go-net-http"]
        self.assertEqual("bar", agent["build"]["args"]["GO_AGENT_BRANCH"])

    def test_agent_go_enable_apm_server(self):
        agent = AgentGoNetHttp(enable_apm_server=True).render()["agent-go-net-http"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentGoNetHttp(enable_apm_server=False).render()["agent-go-net-http"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_go_apm_api_key_with_old_version_apm_server(self):
        agent = AgentGoNetHttp(version="6.3.100", enable_apm_server=True,
                               elastic_apm_api_key="foo").render()["agent-go-net-http"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_go_apm_api_key_with_apm_server(self):
        agent = AgentGoNetHttp(version="7.6", enable_apm_server=True,
                               elastic_apm_api_key="foo").render()["agent-go-net-http"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_nodejs_express(self):
        agent = AgentNodejsExpress().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-nodejs-express:
                    build:
                        dockerfile: Dockerfile
                        context: docker/nodejs/express
                    container_name: expressapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    command: bash -c "npm install elastic-apm-node && node app.js"
                    environment:
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                        ELASTIC_APM_LOG_LEVEL: 'info'
                        EXPRESS_SERVICE_NAME: expressapp
                        EXPRESS_PORT: "8010"
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://expressapp:8010/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8010:8010
            """)  # noqa: 501
        )

        vagent = AgentNodejsExpress(nodejs_agent_package="elastic/apm-agent-nodejs#test").render()
        self.assertEqual('bash -c "npm install elastic/apm-agent-nodejs#test && node app.js"',
                         vagent["agent-nodejs-express"]["command"])

        # test overrides
        agent = AgentNodejsExpress(apm_server_url="http://foo").render()["agent-nodejs-express"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URL"], agent)

    def test_agent_nodejs_express_enable_apm_server(self):
        agent = AgentNodejsExpress(enable_apm_server=True).render()["agent-nodejs-express"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentNodejsExpress(enable_apm_server=False).render()["agent-nodejs-express"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_nodejs_express_apm_api_key_with_old_version_apm_server(self):
        agent = AgentNodejsExpress(version="6.3.100", enable_apm_server=True,
                                   elastic_apm_api_key="foo").render()["agent-nodejs-express"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_nodejs_express_apm_api_key_with_apm_server(self):
        agent = AgentNodejsExpress(version="7.6", enable_apm_server=True,
                                   elastic_apm_api_key="foo").render()["agent-nodejs-express"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_python_django(self):
        agent = AgentPythonDjango().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-python-django:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/django
                    command: bash -c "pip install -q -U elastic-apm && python testapp/manage.py runserver 0.0.0.0:8003"
                    container_name: djangoapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    environment:
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                        DJANGO_SERVICE_NAME: djangoapp
                        DJANGO_PORT: 8003
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://djangoapp:8003/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8003:8003
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentPythonDjango(apm_server_url="http://foo").render()["agent-python-django"]
        self.assertEqual("http://foo", agent["environment"]["APM_SERVER_URL"], agent)

    def test_agent_python_django_enable_apm_server(self):
        agent = AgentPythonDjango(enable_apm_server=True).render()["agent-python-django"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentPythonDjango(enable_apm_server=False).render()["agent-python-django"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_python_django_apm_api_key_with_old_version_apm_server(self):
        agent = AgentPythonDjango(version="6.3.100", enable_apm_server=True,
                                  elastic_apm_api_key="foo").render()["agent-python-django"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_python_django_apm_api_key_with_apm_server(self):
        agent = AgentPythonDjango(version="7.6", enable_apm_server=True,
                                  elastic_apm_api_key="foo").render()["agent-python-django"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_python_flask(self):
        agent = AgentPythonFlask(version="6.2.4").render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-python-flask:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/flask
                    command: bash -c "pip install -q -U elastic-apm && gunicorn app:app"
                    container_name: flaskapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    environment:
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                        FLASK_SERVICE_NAME: flaskapp
                        GUNICORN_CMD_ARGS: "-w 4 -b 0.0.0.0:8001"
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://flaskapp:8001/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8001:8001
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentPythonFlask(apm_server_url="http://foo").render()["agent-python-flask"]
        self.assertEqual("http://foo", agent["environment"]["APM_SERVER_URL"])

    def test_agent_python_flask_enable_apm_server(self):
        agent = AgentPythonFlask(enable_apm_server=True).render()["agent-python-flask"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentPythonFlask(enable_apm_server=False).render()["agent-python-flask"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_python_flask_apm_api_key_with_old_version_apm_server(self):
        agent = AgentPythonFlask(version="6.3.100", enable_apm_server=True,
                                 elastic_apm_api_key="foo").render()["agent-python-flask"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_python_flask_apm_api_key_with_apm_server(self):
        agent = AgentPythonFlask(version="7.6", enable_apm_server=True,
                                 elastic_apm_api_key="foo").render()["agent-python-flask"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_ruby_rails(self):
        agent = AgentRubyRails().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-ruby-rails:
                    build:
                        args:
                            RUBY_AGENT_VERSION: latest
                            RUBY_AGENT_REPO: elastic/apm-agent-ruby
                            RUBY_VERSION: '3.0'
                        dockerfile: Dockerfile
                        context: docker/ruby/rails
                    container_name: railsapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    command: bash -c "bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p 8020"
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_LOG_LEVEL: 1
                        ELASTIC_APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                        ELASTIC_APM_SERVICE_NAME: railsapp
                        RAILS_SERVICE_NAME: railsapp
                        RAILS_PORT: 8020
                        RUBY_AGENT_VERSION: latest
                        RUBY_AGENT_VERSION_STATE: release
                        RUBY_AGENT_REPO: elastic/apm-agent-ruby
                    healthcheck:
                        interval: 10s
                        retries: 60
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://railsapp:8020/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8020:8020
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentRubyRails(apm_server_url="http://foo").render()["agent-ruby-rails"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URL"], agent)

    def test_agent_ruby_with_repo(self):
        agent = AgentRubyRails(ruby_agent_repo="foo/myrepo.git").render()["agent-ruby-rails"]
        self.assertEqual("foo/myrepo.git", agent["environment"]["RUBY_AGENT_REPO"])

    def test_agent_ruby_with_stage(self):
        agent = AgentRubyRails(ruby_agent_version_state="github").render()["agent-ruby-rails"]
        self.assertEqual("github", agent["environment"]["RUBY_AGENT_VERSION_STATE"])

    def test_agent_ruby_with_version(self):
        agent = AgentRubyRails(ruby_agent_version="1.0").render()["agent-ruby-rails"]
        self.assertEqual("1.0", agent["environment"]["RUBY_AGENT_VERSION"])

    def test_agent_ruby_enable_apm_server(self):
        agent = AgentRubyRails(enable_apm_server=True).render()["agent-ruby-rails"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentRubyRails(enable_apm_server=False).render()["agent-ruby-rails"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_ruby_apm_api_key_with_old_version_apm_server(self):
        agent = AgentRubyRails(version="6.3.100", enable_apm_server=True,
                               elastic_apm_api_key="foo").render()["agent-ruby-rails"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_ruby_apm_api_key_with_apm_server(self):
        agent = AgentRubyRails(version="7.6", enable_apm_server=True,
                               elastic_apm_api_key="foo").render()["agent-ruby-rails"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_ruby_version(self):
        agent = AgentRubyRails(ruby_version="2").render()["agent-ruby-rails"]
        self.assertEqual("2", agent["build"]["args"]["RUBY_VERSION"])

    def test_agent_java_spring(self):
        agent = AgentJavaSpring().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-java-spring:
                    build:
                        args:
                            JAVA_AGENT_BRANCH: master
                            JAVA_AGENT_BUILT_VERSION: ""
                            JAVA_AGENT_REPO: elastic/apm-agent-java
                            JAVA_M2_CACHE: "false"
                        dockerfile: Dockerfile
                        context: docker/java/spring
                    container_name: javaspring
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_LOG_LEVEL: 'info'
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                        ELASTIC_APM_SERVICE_NAME: springapp
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output",
                        "/dev/null", "http://javaspring:8090/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8090:8090
            """)
        )

        # test overrides
        agent = AgentJavaSpring(apm_server_url="http://foo").render()["agent-java-spring"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URL"])

    def test_agent_java_with_repo(self):
        agent = AgentJavaSpring(java_agent_repo="foo/myrepo.git").render()["agent-java-spring"]
        self.assertEqual("foo/myrepo.git", agent["build"]["args"]["JAVA_AGENT_REPO"])

    def test_agent_java_with_branch(self):
        agent = AgentJavaSpring(java_agent_version="bar").render()["agent-java-spring"]
        self.assertEqual("bar", agent["build"]["args"]["JAVA_AGENT_BRANCH"])

    def test_agent_java_with_release(self):
        agent = AgentJavaSpring(java_agent_release="1.0").render()["agent-java-spring"]
        self.assertEqual("1.0", agent["build"]["args"]["JAVA_AGENT_BUILT_VERSION"])

    def test_agent_java_enable_apm_server(self):
        agent = AgentJavaSpring(enable_apm_server=True).render()["agent-java-spring"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentJavaSpring(enable_apm_server=False).render()["agent-java-spring"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_java_apm_api_key_with_old_version_apm_server(self):
        agent = AgentJavaSpring(version="6.3.100", enable_apm_server=True,
                                elastic_apm_api_key="foo").render()["agent-java-spring"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_java_apm_api_key_with_apm_server(self):
        agent = AgentJavaSpring(version="7.6", enable_apm_server=True,
                                elastic_apm_api_key="foo").render()["agent-java-spring"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_java_m2_cache(self):
        agent = AgentJavaSpring(java_m2_cache=True).render()["agent-java-spring"]
        self.assertEqual("true", agent["build"]["args"]["JAVA_M2_CACHE"])

    def test_agent_dotnet(self):
        agent = AgentDotnet().render()
        self.assertDictEqual(
            agent, yaml.safe_load("""
                agent-dotnet:
                    build:
                        args:
                            DOTNET_AGENT_BRANCH: main
                            DOTNET_AGENT_VERSION: ""
                            DOTNET_AGENT_REPO: elastic/apm-agent-dotnet
                        dockerfile: Dockerfile
                        context: docker/dotnet
                    container_name: dotnetapp
                    depends_on:
                        apm-server:
                          condition:
                            service_healthy
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_FLUSH_INTERVAL: '5'
                        ELASTIC_APM_LOG_LEVEL: Info
                        ELASTIC_APM_SERVICE_NAME: dotnetapp
                        ELASTIC_APM_TRANSACTION_IGNORE_NAMES: 'healthcheck'
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output",
                        "/dev/null", "http://dotnetapp:8100/healthcheck"]
                        timeout: 5s
                    ports:
                        - 127.0.0.1:8100:8100
            """)
        )

        # test overrides
        agent = AgentDotnet(apm_server_url="http://foo").render()["agent-dotnet"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URLS"])

    def test_agent_dotnet_with_repo(self):
        agent = AgentDotnet(dotnet_agent_repo="foo/myrepo.git").render()["agent-dotnet"]
        self.assertEqual("foo/myrepo.git", agent["build"]["args"]["DOTNET_AGENT_REPO"])

    def test_agent_dotnet_with_branch(self):
        agent = AgentDotnet(dotnet_agent_version="bar").render()["agent-dotnet"]
        self.assertEqual("bar", agent["build"]["args"]["DOTNET_AGENT_BRANCH"])

    def test_agent_dotnet_with_release(self):
        agent = AgentDotnet(dotnet_agent_release="1.0").render()["agent-dotnet"]
        self.assertEqual("1.0", agent["build"]["args"]["DOTNET_AGENT_VERSION"])

    def test_agent_dotnet_enable_apm_server(self):
        agent = AgentDotnet(enable_apm_server=True).render()["agent-dotnet"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentDotnet(enable_apm_server=False).render()["agent-dotnet"]
        self.assertFalse("apm-server" in agent["depends_on"])

    def test_agent_dotnet_apm_api_key_with_old_version_apm_server(self):
        agent = AgentDotnet(version="6.3.100", enable_apm_server=True,
                            elastic_apm_api_key="foo").render()["agent-dotnet"]
        self.assertFalse("ELASTIC_APM_API_KEY" in agent["environment"])

    def test_agent_dotnet_apm_api_key_with_apm_server(self):
        agent = AgentDotnet(version="7.6", enable_apm_server=True, elastic_apm_api_key="foo").render()["agent-dotnet"]
        self.assertEqual("foo", agent["environment"]["ELASTIC_APM_API_KEY"])

    def test_agent_php(self):
        agent = AgentPhpApache().render()
        self.assertDictEqual(
<<<<<<< HEAD:scripts/tests/test_service.py
            agent, yaml.safe_load("""
                agent-php-apache:
                    build:
                        args:
                            PHP_AGENT_BRANCH: main
=======
            agent, yaml.load("""
                agent-php-apache:
                    build:
                        args:
                            PHP_AGENT_BRANCH: master
>>>>>>> 4c63a2a (support PHP ITs (#946)):scripts/tests/service_tests.py
                            PHP_AGENT_VERSION: ""
                            PHP_AGENT_REPO: elastic/apm-agent-php
                        dockerfile: Dockerfile
                        context: docker/php/apache
                    container_name: phpapacheapp
                    depends_on:
                        apm-server:
<<<<<<< HEAD:scripts/tests/test_service.py
                          condition:
                            service_healthy
=======
                            condition: 'service_healthy'
>>>>>>> 4c63a2a (support PHP ITs (#946)):scripts/tests/service_tests.py
                    environment:
                        ELASTIC_APM_SERVICE_NAME: 'phpapacheapp'
                        ELASTIC_APM_VERIFY_SERVER_CERT: 'true'
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output",
                        "/dev/null", "http://phpapacheapp:80/healthcheck"]
<<<<<<< HEAD:scripts/tests/test_service.py
                        timeout: 5s
=======
>>>>>>> 4c63a2a (support PHP ITs (#946)):scripts/tests/service_tests.py
                    ports:
                        - 127.0.0.1:8030:80
            """)
        )

        # test overrides
        agent = AgentPhpApache(apm_server_url="http://foo").render()["agent-php-apache"]
        self.assertEqual("http://foo", agent["environment"]["ELASTIC_APM_SERVER_URL"])

    def test_agent_php_with_repo(self):
        agent = AgentPhpApache(php_agent_repo="foo/myrepo.git").render()["agent-php-apache"]
        self.assertEqual("foo/myrepo.git", agent["build"]["args"]["PHP_AGENT_REPO"])

    def test_agent_php_with_branch(self):
        agent = AgentPhpApache(php_agent_version="bar").render()["agent-php-apache"]
        self.assertEqual("bar", agent["build"]["args"]["PHP_AGENT_BRANCH"])

    def test_agent_php_with_release(self):
        agent = AgentPhpApache(php_agent_release="1.0").render()["agent-php-apache"]
        self.assertEqual("1.0", agent["build"]["args"]["PHP_AGENT_VERSION"])

    def test_agent_php_enable_apm_server(self):
        agent = AgentPhpApache(enable_apm_server=True).render()["agent-php-apache"]
        self.assertTrue("apm-server" in agent["depends_on"])

        agent = AgentPhpApache(enable_apm_server=False).render()["agent-php-apache"]
        self.assertFalse("apm-server" in agent["depends_on"])
<<<<<<< HEAD:scripts/tests/test_service.py

=======
>>>>>>> 4c63a2a (support PHP ITs (#946)):scripts/tests/service_tests.py

class ApmServerServiceTest(ServiceTest):
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

    def test_ubi8_snapshot(self):
        apm_server = ApmServer(version="8.0.0", ubi8=True, snapshot=True).render()["apm-server"]
        self.assertEqual(
            apm_server["image"], "docker.elastic.co/apm/apm-server-ubi8:8.0.0-SNAPSHOT"
        )

    def test_api_key_auth(self):
        apm_server = ApmServer(version="7.6.100", apm_server_api_key_auth=True).render()["apm-server"]
        self.assertIn("apm-server.api_key.enabled=true", apm_server["command"])

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
        self.assertTrue("elasticsearch" in apm_server["depends_on"])
        self.assertTrue("kibana" in apm_server["depends_on"])
        self.assertTrue("output.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in apm_server["command"])

    def test_elasticsearch_output_overrides(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="elasticsearch",
                               apm_server_elasticsearch_urls=["foo:123", "bar:456"],
                               apm_server_elasticsearch_username="apmuser",
                               apm_server_elasticsearch_password="secretpassword",
                               ).render()["apm-server"]
        self.assertFalse(
            any(e.startswith("xpack.monitoring.elasticsearch.hosts=") for e in apm_server["command"]),
            "xpack.monitoring.elasticsearch.hosts while output=elasticsearch and overrides set"
        )
        elasticsearch_options = [
            "output.elasticsearch.hosts=[\"foo:123\", \"bar:456\"]",
            "output.elasticsearch.username=apmuser",
            "output.elasticsearch.password=secretpassword",
        ]
        for o in elasticsearch_options:
            self.assertTrue(o in apm_server["command"],
                            "{} not set while output=elasticsearch and overrides set: ".format(o) + " ".join(
                                apm_server["command"]))

    def test_elasticsearch_output_tls(self):
        apm_server = ApmServer(version="7.8.100", apm_server_output="elasticsearch",
                               elasticsearch_enable_tls=True,
                               ).render()["apm-server"]
        self.assertTrue("output.elasticsearch.ssl.certificate_authorities=['/usr/share/apm-server/config/certs/stack-ca.crt']" in apm_server["command"],
                        "CA not set when elasticsearch TLS is enabled")

    def test_ilm_default(self):
        """enable ILM by default in 7.2+"""
        apm_server = ApmServer(version="6.3.100").render()["apm-server"]
        self.assertFalse("apm-server.ilm.enabled=true" in
                         apm_server["command"], "ILM not enabled by default in < 7.2")

        apm_server = ApmServer(version="7.2.0").render()["apm-server"]
        self.assertTrue("apm-server.ilm.enabled=true" in apm_server["command"],
                        "ILM enabled by default in = 7.2")

        apm_server = ApmServer(version="7.3.0").render()["apm-server"]
        self.assertTrue("apm-server.ilm.enabled" not in apm_server["command"],
                        "ILM auto by default in >= 7.3")

    def test_ilm_disabled(self):
        apm_server = ApmServer(version="7.2.0", apm_server_ilm_disable=True).render()["apm-server"]
        self.assertFalse("apm-server.ilm.enabled=true" in apm_server["command"], "ILM enabled but should not be")

    def test_file_output(self):
        apm_server = ApmServer(version="7.3.100", apm_server_output="file").render()["apm-server"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.file.enabled=true",
            "output.file.path=" + os.devnull,
            "monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=file".format(o))

    def test_monitoring_options_6(self):
        apm_server = ApmServer(version="6.8.0", apm_server_output="file").render()["apm-server"]
        self.assertTrue("xpack.monitoring.enabled=true" in apm_server["command"])
        self.assertTrue("xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in apm_server["command"])

    def test_monitoring_options_71(self):
        apm_server = ApmServer(version="7.1.0", apm_server_output="file").render()["apm-server"]
        self.assertTrue("xpack.monitoring.enabled=true" in apm_server["command"])
        self.assertTrue("xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in apm_server["command"])

    def test_monitoring_options_post_72(self):
        apm_server = ApmServer(version="7.2.0", apm_server_output="file").render()["apm-server"]
        self.assertTrue("monitoring.enabled=true" in apm_server["command"])
        self.assertTrue("monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in apm_server["command"])

    def test_file_output_path(self):
        apm_server = ApmServer(version="7.3.100", apm_server_output="file",
                               apm_server_output_file="foo").render()["apm-server"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.file.enabled=true",
            "output.file.path=foo",
            "monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=file".format(o))

    def test_logstash_output(self):
        apm_server = ApmServer(version="7.3.0", apm_server_output="logstash").render()["apm-server"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=logstash".format(o))

    def test_logstash_output_overrides(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="logstash",
                               apm_server_elasticsearch_urls=["foo:123", "bar:456"],
                               apm_server_elasticsearch_username="apmuser",
                               apm_server_elasticsearch_password="secretpassword",
                               ).render()["apm-server"]
        options = [
            "xpack.monitoring.elasticsearch.hosts=[\"foo:123\", \"bar:456\"]",
            "xpack.monitoring.elasticsearch.username=apmuser",
            "xpack.monitoring.elasticsearch.password=secretpassword",
        ]
        for o in options:
            self.assertTrue(o in apm_server["command"],
                            "{} not set while output=logstash and overrides set: ".format(o) + " ".join(
                                apm_server["command"]))

    def test_kafka_output(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="kafka").render()["apm-server"]
        self.assertTrue(
            "xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in apm_server["command"],
            "xpack.monitoring.elasticsearch.hosts not set while output=kafka"
        )
        self.assertTrue(
            any(e == "output.elasticsearch.enabled=false" for e in apm_server["command"]),
            "output.elasticsearch.enabled not false while output=elasticsearch"
        )
        kafka_options = [
            "output.kafka.enabled=true",
            "output.kafka.hosts=[\"kafka:9092\"]",
            "output.kafka.topics=[{default: 'apm', topic: 'apm-%{[service.name]}'}]",
        ]
        for o in kafka_options:
            self.assertTrue(o in apm_server["command"], "{} not set while output=kafka".format(o))

    def test_kibana_tls(self):
        apm_server = ApmServer(version="7.8.100", kibana_enable_tls=True).render()["apm-server"]
        self.assertTrue(
            "apm-server.kibana.ssl.certificate_authorities=[\"/usr/share/apm-server/config/certs/stack-ca.crt\"]" in apm_server["command"],
            "CA not set when kibana TLS is enabled"
        )

    def test_opt(self):
        apm_server = ApmServer(version="7.1.10", apm_server_opt=("an.opt=foo", "opt2=bar")).render()["apm-server"]
        self.assertTrue(
            any(e.startswith("an.opt") for e in apm_server["command"]),
            "some.option should be set "
        )
        self.assertTrue(
            any(e.startswith("opt2") for e in apm_server["command"]),
            "some.option should be set "
        )

    def test_pipeline(self):
        def get_pipelines(command):
            # also checks that output.elasticsearch.pipeline isn't set
            got = [e.split("=", 1) for e in command if e.startswith("output.elasticsearch.pipeline")]
            # ensure single output.elasticsearch.pipeline setting, should be output.elasticsearch.pipelines=
            self.assertEqual(1, len(got))
            directive, setting = got[0]
            self.assertEqual("output.elasticsearch.pipelines", directive)
            return yaml.safe_load(setting)

        apm_server = ApmServer(version="6.5.10").render()["apm-server"]
        self.assertEqual(get_pipelines(apm_server["command"]), [{'pipeline': 'apm_user_agent'}],
                         "output.elasticsearch.pipelines should be set to apm_user_agent in 7.2 > version >= 6.5")

        apm_server = ApmServer(version="7.2.0", apm_server_enable_pipeline=True).render()["apm-server"]
        self.assertEqual(get_pipelines(apm_server["command"]), [{'pipeline': 'apm'}],
                         "output.elasticsearch.pipelines should be set to apm in version >= 7.2")

        apm_server = ApmServer(version="6.5.10", apm_server_enable_pipeline=False).render()["apm-server"]
        self.assertFalse(
            any(e.startswith("output.elasticsearch.pipelines") for e in apm_server["command"]),
            "output.elasticsearch.pipelines set while apm_server_enable_pipeline=False"
        )

        apm_server = ApmServer(version="6.5.10", apm_server_output="logstash").render()["apm-server"]
        self.assertFalse(
            any(e.startswith("output.elasticsearch.pipelines") for e in apm_server["command"]),
            "output.elasticsearch.pipelines set while output is not elasticsearch"
        )

        apm_server = ApmServer(version="6.4.10", apm_server_enable_pipeline=True).render()["apm-server"]
        self.assertFalse(
            any(e.startswith("output.elasticsearch.pipelines") for e in apm_server["command"]),
            "output.elasticsearch.pipelines set while apm_server_enable_pipeline=False in version < 6.5"
        )

    def test_queue_file(self):
        cases = [
            (
                dict(),
                {"file": {"path": "$${path.data}/spool.dat"}},
            ),
            (
                dict(apm_server_queue_file_size="200MiB"),
                {"file": {"path": "$${path.data}/spool.dat", "size": "200MiB"}},
            ),
            (
                dict(apm_server_queue_write_flush_timeout="0s"),
                {"file": {"path": "$${path.data}/spool.dat"}, "write": {"flush.timeout": "0s"}},
            ),
        ]
        for opts, want in cases:
            apm_server = ApmServer(version="7.1.10", apm_server_queue="file", **opts).render()["apm-server"]
            got = [e.split("=", 1)[1] for e in apm_server["command"] if e.startswith("queue.spool=")]
            self.assertEqual(1, len(got))
            self.assertEqual(json.loads(got[0]), want)

    def test_queue_mem(self):
        apm_server = ApmServer(version="7.1.10", apm_server_queue="mem").render()["apm-server"]
        self.assertFalse(
            any(e.startswith("queue.") for e in apm_server["command"]),
            "no queue settings with memory queue (for now)"
        )

    def test_self_instrument(self):
        # self instrumentation comes with profiling by default
        apm_server = ApmServer(version="8.0.0").render()["apm-server"]
        self.assertIn("apm-server.instrumentation.enabled=true", apm_server["command"])
        self.assertIn("apm-server.instrumentation.profiling.cpu.enabled=true", apm_server["command"])
        self.assertIn("apm-server.instrumentation.profiling.heap.enabled=true", apm_server["command"])

        # self instrumentation comes with profiling by default but can be disabled
        apm_server = ApmServer(
            version="8.0.0", apm_server_self_instrument=True, apm_server_profile=False).render()["apm-server"]
        self.assertIn("apm-server.instrumentation.enabled=true", apm_server["command"])
        self.assertFalse(
            any(e.startswith("apm-server.instrumentation.profiling") for e in apm_server["command"]),
            "no self profiling settings expected"
        )

        # need self instrumentation enabled to get profiling
        apm_server = ApmServer(
            version="8.0.0", apm_server_self_instrument=False, apm_server_profile=True).render()["apm-server"]
        self.assertNotIn("apm-server.instrumentation.enabled=true", apm_server["command"])
        self.assertNotIn("apm-server.instrumentation.profiling.cpu.enabled=true", apm_server["command"])
        self.assertNotIn("apm-server.instrumentation.profiling.heap.enabled=true", apm_server["command"])

    def test_apm_server_build_branch(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git@bar", release=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server:6.3.100',
                     'apm_server_binary': 'apm-server',
                     'apm_server_branch_or_commit': 'bar',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_branch_default(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git", release=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server:6.3.100',
                     'apm_server_binary': 'apm-server',
                     'apm_server_branch_or_commit': 'master',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_oss(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git",
                               release=True, oss=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server-oss:6.3.100',
                     'apm_server_binary': 'apm-server-oss',
                     'apm_server_branch_or_commit': 'master',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_ubi8(self):
        apm_server = ApmServer(version="7.9.2", apm_server_build="foo.git",
                               release=True, ubi8=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server-ubi8:7.9.2',
                     'apm_server_binary': 'apm-server',
                     'apm_server_branch_or_commit': 'master',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_count(self):
        render = ApmServer(version="6.4.100", apm_server_count=2).render()
        apm_server_lb = render["apm-server"]
        apm_server_2 = render["apm-server-2"]
        self.assertDictEqual(apm_server_lb["build"], {"context": "docker/apm-server/haproxy"})
        self.assertListEqual(["127.0.0.1:8200:8200"], apm_server_lb["ports"], apm_server_lb["ports"])
        self.assertListEqual(["8200", "6060"], apm_server_2["ports"], apm_server_2["ports"])

    def test_apm_server_record(self):
        render = ApmServer(version="6.4.100", apm_server_record=True).render()
        apm_server_lb = render["apm-server"]
        self.assertIn("build", apm_server_lb)

    def test_apm_server_tee(self):
        render = ApmServer(version="6.4.100", apm_server_tee=True).render()
        apm_server_lb = render["apm-server"]
        apm_server_2 = render["apm-server-2"]
        self.assertIn("build", apm_server_lb)
        self.assertDictEqual(apm_server_lb["build"], {"context": "docker/apm-server/teeproxy"})
        self.assertListEqual(["127.0.0.1:8200:8200"], apm_server_lb["ports"], apm_server_lb["ports"])
        self.assertListEqual(["8200", "6060"], apm_server_2["ports"], apm_server_2["ports"])

    def test_apm_server_tee_multi(self):
        render = ApmServer(version="6.4.100", apm_server_count=4, apm_server_tee=True).render()
        apm_server_lb = render["apm-server"]
        apm_server_4 = render["apm-server-4"]
        self.assertListEqual(apm_server_lb["command"],
                             ["teeproxy", "-l", "0.0.0.0:8200", "-a", "apm-server-1:8200",
                              "-b", "apm-server-2:8200", "-b", "apm-server-3:8200", "-b", "apm-server-4:8200"])
        self.assertIn("build", apm_server_lb)
        self.assertDictEqual(apm_server_lb["build"], {"context": "docker/apm-server/teeproxy"})
        self.assertListEqual(["127.0.0.1:8200:8200"], apm_server_lb["ports"], apm_server_lb["ports"])
        self.assertListEqual(["8200", "6060"], apm_server_4["ports"], apm_server_4["ports"])

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
        self.assertEqual(apm_server["labels"], ["co.elastic.apm.stack-version=6.12.0"])

    def test_dashboards(self):
        apm_server = ApmServer(version="6.3.100", apm_server_dashboards=False).render()["apm-server"]
        self.assertFalse(
            any(e.startswith("setup.dashboards.enabled=") for e in apm_server["command"]),
            "setup.dashboards.enabled while apm_server_dashboards=False"
        )

        apm_server = ApmServer(version="6.3.100", enable_kibana=False).render()["apm-server"]
        self.assertFalse(
            any(e.startswith("setup.dashboards.enabled=") for e in apm_server["command"]),
            "setup.dashboards.enabled while enable_kibana=False"
        )

    def test_apm_server_acm(self):
        apm_server = ApmServer(version="7.3").render()["apm-server"]
        self.assertTrue("apm-server.kibana.enabled=true" in apm_server["command"],
                        "APM Server Kibana enabled by default")

        apm_server = ApmServer(version="7.3", apm_server_acm_disable=True).render()["apm-server"]
        self.assertTrue("apm-server.kibana.enabled=false" in apm_server["command"],
                        "APM Server Kibana disabled when apm_server_disable_kibana=True")

        apm_server = ApmServer(version="7.3", xpack_secure=True).render()["apm-server"]
        self.assertTrue("apm-server.kibana.username=apm_server_user" in apm_server["command"],
                        "APM Server Kibana username set by default")
        self.assertTrue("apm-server.kibana.password=changeme" in apm_server["command"],
                        "APM Server Kibana password set by default")

        apm_server = ApmServer(version="7.3", xpack_secure=True,
                               apm_server_elasticsearch_username="another_apm_server_user",
                               apm_server_elasticsearch_password="notchangeme").render()["apm-server"]
        self.assertTrue("apm-server.kibana.username=another_apm_server_user" in apm_server["command"],
                        "APM Server Kibana username overridden")
        self.assertTrue("apm-server.kibana.password=notchangeme" in apm_server["command"],
                        "APM Server Kibana password overridden")

    def test_apm_server_custom_pipeline(self):
        apm_server = ApmServer(version="8.0", apm_server_pipeline_path="foo").render()["apm-server"]
        self.assertIn("foo:/usr/share/apm-server/ingest/pipeline/definition.json", apm_server["volumes"])
        self.assertIn("apm-server.register.ingest.pipeline.overwrite=true", apm_server["command"])

    def test_data_streams(self):
        apm_server = ApmServer(version="7.16.0", apm_server_enable_data_streams=True).render()["apm-server"]
        self.assertIn("apm-server.data_streams.enabled=true", apm_server["command"])
        self.assertFalse(
            any(a.startswith("output.elasticsearch.pipelines=") for a in apm_server["command"]),
            "output.elasticsearch.pipelines with data streams enabled",
        )

    def test_debug(self):
        apm_server = ApmServer(version="6.8.0", apm_server_enable_debug=True).render()["apm-server"]
        self.assertTrue("-d" in apm_server["command"])
        self.assertTrue("*" in apm_server["command"])


class ElasticAgentServiceTest(ServiceTest):
    def test_default(self):
        ea = ElasticAgent(version="7.12.345", enable_apm_server=True, apm_server_managed=True).render()["elastic-agent"]
        self.assertEqual(
            ea, {"container_name": "localtesting_7.12.345_elastic-agent",
                 "depends_on": {"kibana": {"condition": "service_healthy"}},
                 'environment': {'ELASTICSEARCH_HOST': 'http://admin:changeme@elasticsearch:9200',
                                 'ELASTICSEARCH_PASSWORD': 'changeme',
                                 'ELASTICSEARCH_USERNAME': 'admin',
                                 'FLEET_ENROLL': '1',
                                 'FLEET_ENROLL_INSECURE': 1,
                                 'FLEET_SERVER_ENABLE': '1',
                                 'FLEET_INSECURE': '1',
                                 "FLEET_SERVER_INSECURE_HTTP": "1",
                                 'FLEET_SERVER_HOST': '0.0.0.0',
                                 'FLEET_SETUP': '1',
                                 'KIBANA_FLEET_SETUP': '1',
                                 'KIBANA_HOST': 'http://admin:changeme@kibana:5601',
                                 'KIBANA_PASSWORD': 'changeme',
                                 'KIBANA_USERNAME': 'admin'},
                 "healthcheck": {"test": ["CMD", "/bin/true"]},
                 "image": "docker.elastic.co/beats/elastic-agent:7.12.345-SNAPSHOT",
                 "labels": ["co.elastic.apm.stack-version=7.12.345"],
                 "logging": {"driver": "json-file",
                             "options": {"max-file": "5", "max-size": "2m"}},
                 'ports': ['127.0.0.1:8220:8220', '127.0.0.1:8200:8200'],
                 "volumes": ["/var/run/docker.sock:/var/run/docker.sock"]}
        )

    def test_default_snapshot(self):
        ea = ElasticAgent(version="7.12.345", snapshot=True).render()["elastic-agent"]
        self.assertEqual(
            "docker.elastic.co/beats/elastic-agent:7.12.345-SNAPSHOT", ea["image"]
        )

    def test_kibana_tls(self):
        ea = ElasticAgent(version="7.12.345", kibana_enable_tls=True).render()["elastic-agent"]
        self.assertEqual(
            "https://admin:changeme@kibana:5601", ea["environment"]["KIBANA_HOST"]
        )

    def test_kibana_url(self):
        ea = ElasticAgent(version="7.12.345", elastic_agent_kibana_url="http://foo").render()["elastic-agent"]
        self.assertEqual("http://foo", ea["environment"]["KIBANA_HOST"])
        self.assertNotIn("KIBANA_PASSWORD", ea["environment"])
        self.assertNotIn("KIBANA_USERNAME", ea["environment"])

        ea = ElasticAgent(version="7.12.345", elastic_agent_kibana_url="http://u:p@h:123").render()["elastic-agent"]
        self.assertEqual("http://u:p@h:123", ea["environment"]["KIBANA_HOST"])
        self.assertEqual("p", ea["environment"]["KIBANA_PASSWORD"])
        self.assertEqual("u", ea["environment"]["KIBANA_USERNAME"])


class PackageRegistryServiceTest(ServiceTest):
    def test_default(self):
        epr = PackageRegistry(version="7.11").render()["package-registry"]
        self.assertEqual(
            epr, {'image': 'docker.elastic.co/package-regis[456 chars]m',
                  'container_name': 'localtesting_7.11_package-registry',
                  'environment': {},
                  'healthcheck': {'interval': '5s',
                                  'retries': 10,
                                  'timeout': '5s',
                                  'test': ['CMD',
                                           'curl',
                                           '--write-out',
                                           "'HTTP %{http_code}'",
                                           '-k',
                                           '--fail',
                                           '--silent',
                                           '--output',
                                           '/dev/null',
                                           'http://localhost:8080/']},
                  'image': 'docker.elastic.co/package-registry/distribution:snapshot',
                  'labels': ['co.elastic.apm.stack-version=7.11'],
                  'logging': {'driver': 'json-file',
                              'options': {'max-file': '5', 'max-size': '2m'}},
                  'ports': ['127.0.0.1:8080:8080']}
        )

    def test_production(self):
        epr = PackageRegistry(version="7.11", package_registry_distribution="production").render()["package-registry"]
        self.assertEqual(
            epr, {'image': 'docker.elastic.co/package-regis[456 chars]m',
                  'container_name': 'localtesting_7.11_package-registry',
                  'environment': {},
                  'healthcheck': {'interval': '5s',
                                  'retries': 10,
                                  'timeout': '5s',
                                  'test': ['CMD',
                                           'curl',
                                           '--write-out',
                                           "'HTTP %{http_code}'",
                                           '-k',
                                           '--fail',
                                           '--silent',
                                           '--output',
                                           '/dev/null',
                                           'http://localhost:8080/']},
                  'image': 'docker.elastic.co/package-registry/distribution:production',
                  'labels': ['co.elastic.apm.stack-version=7.11'],
                  'logging': {'driver': 'json-file',
                              'options': {'max-file': '5', 'max-size': '2m'}},
                  'ports': ['127.0.0.1:8080:8080']}
        )


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

    def test_7_10_ubi8_release(self):
        elasticsearch = Elasticsearch(version="7.10.0", ubi8=True, release=True).render()["elasticsearch"]
        self.assertEqual(
            elasticsearch["image"], "docker.elastic.co/elasticsearch/elasticsearch-ubi8:7.10.0"
        )
        self.assertTrue(
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

    def test_6_8_14_oss_release_not_supported(self):
        with self.assertRaises(SystemExit) as cm:
            elasticsearch = Elasticsearch(version="6.8.14", oss=True, release=True).render()["elasticsearch"]
        self.assertEqual(cm.exception.code, 1)

    def test_6_9_oss_release_supported(self):
        elasticsearch = Elasticsearch(version="6.9", oss=True, release=True).render()["elasticsearch"]
        self.assertEqual(
            elasticsearch["image"], "docker.elastic.co/elasticsearch/elasticsearch-oss:6.9"
        )

    def test_7_11_oss_release_not_supported(self):
        with self.assertRaises(SystemExit) as cm:
            elasticsearch = Elasticsearch(version="7.11.0", oss=True, release=True).render()["elasticsearch"]
        self.assertEqual(cm.exception.code, 1)

    def test_data_dir(self):
        # default
        elasticsearch = Elasticsearch(version="6.3.100").render()["elasticsearch"]
        data_path = [e for e in elasticsearch["environment"] if e.startswith("path.data=")]
        self.assertListEqual(["path.data=/usr/share/elasticsearch/data/6.3.100"], data_path)

        # override empty
        elasticsearch = Elasticsearch(version="6.3.100", elasticsearch_data_dir="").render()["elasticsearch"]
        data_path = [e for e in elasticsearch["environment"] if e.startswith("path.data=")]
        self.assertListEqual(["path.data=/usr/share/elasticsearch/data/"], data_path)

        # override non-empty
        elasticsearch = Elasticsearch(version="6.3.100", elasticsearch_data_dir="foo").render()["elasticsearch"]
        data_path = [e for e in elasticsearch["environment"] if e.startswith("path.data=")]
        self.assertListEqual(["path.data=/usr/share/elasticsearch/data/foo"], data_path)

    def test_heap(self):
        elasticsearch = Elasticsearch(version="6.3.100", elasticsearch_heap="5m").render()["elasticsearch"]
        java_opts = [e for e in elasticsearch["environment"] if e.startswith("ES_JAVA_OPTS=")]
        self.assertListEqual(["ES_JAVA_OPTS=-Xms5m -Xmx5m"], java_opts)

    def test_java_opts(self):
        elasticsearch = Elasticsearch(
            version="6.3.100", elasticsearch_java_opts={"XX:+UseConcMarkSweepGC": ""}).render()["elasticsearch"]
        java_opts = [e for e in elasticsearch["environment"] if e.startswith("ES_JAVA_OPTS=")]
        self.assertListEqual(["ES_JAVA_OPTS=-XX:+UseConcMarkSweepGC"], java_opts)

    def test_snapshot(self):
        elasticsearch = Elasticsearch(version="7.11.100", elasticsearch_snapshot_repo=["http://single_repo.url/p/ath"]).render()["elasticsearch"]
        repos_allowed = [e for e in elasticsearch["environment"] if e.startswith("repositories.url.allowed_urls=")]
        self.assertEqual(["repositories.url.allowed_urls=http://single_repo.url/p/ath"], repos_allowed)

        elasticsearch = Elasticsearch(version="7.11.100", elasticsearch_snapshot_repo=["http://first_repo.url/p/ath", "http://second_repo.url/p/ath"]).render()["elasticsearch"]
        repos_allowed = [e for e in elasticsearch["environment"] if e.startswith("repositories.url.allowed_urls=")]
        self.assertEqual(["repositories.url.allowed_urls=http://first_repo.url/p/ath,http://second_repo.url/p/ath"], repos_allowed)

    def test_tls(self):
        elasticsearch = Elasticsearch(version="7.11.100", elasticsearch_tls_enable=True).render()["elasticsearch"]
        self.assertListEqual(["co.elastic.apm.stack-version=7.11.100",
                              "co.elastic.metrics/module=elasticsearch",
                              "co.elastic.metrics/metricsets=node,node_stats",
                              "co.elastic.metrics/hosts=http://$${data.host}:9200"
                              ], elasticsearch["labels"])


class EnterpriseSearchServiceTest(ServiceTest):
    def test_release(self):
        entsearch = EnterpriseSearch(version="7.12.20", release=True).render()["enterprise-search"]
        self.assertEqual(
            entsearch["image"], "docker.elastic.co/enterprise-search/enterprise-search:7.12.20"
        )

    def test_8_0_0(self):
        entsearch = EnterpriseSearch(version="8.0.0").render()["enterprise-search"]
        self.assertEqual(
            entsearch["image"], "docker.elastic.co/enterprise-search/enterprise-search:8.0.0-SNAPSHOT"
        )
        self.assertDictContainsSubset({"apm.enabled": "true", "kibana.external_url": "http://localhost:5601", "kibana.host": "http://kibana:5601"}, entsearch["environment"])
        kibana = Kibana(version="8.0.0", with_enterprise_search=True).render()["kibana"]
        self.assertDictContainsSubset({"ENTERPRISESEARCH_HOST": "http://enterprise-search:3002"}, kibana["environment"])


class FilebeatServiceTest(ServiceTest):
    def test_filebeat_pre_6_1(self):
        filebeat = Filebeat(version="6.0.4", release=True).render()
        self.assertEqual(
            filebeat, yaml.safe_load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.0.4
                    container_name: localtesting_6.0.4_filebeat
                    user: root
                    command: ["filebeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                        kibana:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://localhost:5066/?pretty"]
                        interval: 10s
                        retries: 12
                        timeout: 5s
                    volumes:
                        - ./docker/filebeat/filebeat.simple.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock
                        - ./scripts/tls/ca/ca.crt:/usr/share/beats/config/certs/stack-ca.crt""")
        )

    def test_filebeat_post_6_1(self):
        filebeat = Filebeat(version="6.1.1", release=True).render()
        self.assertEqual(
            filebeat, yaml.safe_load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.1.1
                    container_name: localtesting_6.1.1_filebeat
                    user: root
                    command: ["filebeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                        kibana:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://localhost:5066/?pretty"]
                        interval: 10s
                        retries: 12
                        timeout: 5s
                    volumes:
                        - ./docker/filebeat/filebeat.6.x-compat.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock
                        - ./scripts/tls/ca/ca.crt:/usr/share/beats/config/certs/stack-ca.crt""")
        )

    def test_filebeat_7_1(self):
        filebeat = Filebeat(version="7.1.0", release=True).render()
        self.assertTrue(
            "./docker/filebeat/filebeat.6.x-compat.yml:/usr/share/filebeat/filebeat.yml" in filebeat["filebeat"]["volumes"])

    def test_filebeat_post_7_2(self):
        filebeat = Filebeat(version="7.2.0", release=True).render()
        self.assertTrue(
            "./docker/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml" in filebeat["filebeat"]["volumes"])

    def test_filebeat_elasticsearch_output_tls(self):
        filebeat = Filebeat(version="7.8.100", elasticsearch_enable_tls=True).render()["filebeat"]
        self.assertTrue(
            "output.elasticsearch.ssl.certificate_authorities=['/usr/share/beats/config/certs/stack-ca.crt']" in
            filebeat["command"],
            "CA not set when elasticsearch TLS is enabled")

    def test_filebeat_elasticsearch_urls(self):
        filebeat = Filebeat(version="6.1.1", release=True, filebeat_elasticsearch_urls=[
                            "elasticsearch01:9200"]).render()["filebeat"]
        self.assertTrue("elasticsearch" in filebeat['depends_on'])
        self.assertTrue("output.elasticsearch.hosts=[\"elasticsearch01:9200\"]" in filebeat['command'])

        filebeat = Filebeat(version="6.1.1", release=True, filebeat_elasticsearch_urls=[
                            "elasticsearch01:9200", "elasticsearch02:9200"]).render()["filebeat"]
        self.assertTrue("elasticsearch" in filebeat['depends_on'])
        self.assertTrue(
            "output.elasticsearch.hosts=[\"elasticsearch01:9200\", \"elasticsearch02:9200\"]" in filebeat['command'])

    def test_logstash_output(self):
        beat = Filebeat(version="6.3.100", filebeat_output="logstash").render()["filebeat"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in beat["command"], "{} not set in {} while output=logstash".format(o, beat["command"]))


class KafkaServiceTest(ServiceTest):
    def test_kafka(self):
        kafka = Kafka(version="6.2.4").render()
        self.assertEqual(
            kafka, yaml.safe_load("""
                kafka:
                    image: confluentinc/cp-kafka:4.1.3
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
            kibana, yaml.safe_load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana-x-pack:6.2.4
                    container_name: localtesting_6.2.4_kibana
                    environment:
                        SERVER_HOST: 0.0.0.0
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_HOSTS: http://elasticsearch:9200
                        XPACK_MONITORING_ENABLED: 'true'
                    ports:
                        - "127.0.0.1:5601:5601"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://kibana:5601/api/status"]
                        interval: 10s
                        retries: 30
                        timeout: 5s
                        start_period: 10s
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                    labels:
                        - co.elastic.apm.stack-version=6.2.4""")  # noqa: 501
        )

    def test_6_3_release(self):
        kibana = Kibana(version="6.3.5", release=True).render()
        self.assertDictEqual(
            kibana, yaml.safe_load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana:6.3.5
                    container_name: localtesting_6.3.5_kibana
                    environment:
                        SERVER_HOST: 0.0.0.0
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_HOSTS: http://elasticsearch:9200
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
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://kibana:5601/api/status"]
                        timeout: 5s
                        interval: 10s
                        retries: 30
                        start_period: 10s
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                    labels:
                        - co.elastic.apm.stack-version=6.3.5""")  # noqa: 501
        )

    def test_6_8_14_oss_release_not_supported(self):
        with self.assertRaises(SystemExit) as cm:
            kibana = Kibana(version="6.8.14", oss=True, release=True).render()["kibana"]
        self.assertEqual(cm.exception.code, 1)

    def test_6_9_oss_release_supported(self):
        kibana = Kibana(version="6.9", oss=True, release=True).render()["kibana"]
        self.assertEqual(
            kibana["image"], "docker.elastic.co/kibana/kibana-oss:6.9"
        )

    def test_7_11_oss_release_not_supported(self):
        with self.assertRaises(SystemExit) as cm:
            kibana = Kibana(version="7.11.1", oss=True, release=True).render()["kibana"]
        self.assertEqual(cm.exception.code, 1)

    def test_kibana_elasticsearch_urls(self):
        kibana = Kibana(version="6.3.5", release=True, kibana_elasticsearch_urls=[
                        "elasticsearch01:9200"]).render()["kibana"]
        self.assertTrue("elasticsearch" in kibana['depends_on'])
        self.assertEqual("elasticsearch01:9200", kibana['environment']["ELASTICSEARCH_HOSTS"])

        kibana = Kibana(version="6.3.5", release=True, kibana_elasticsearch_urls=[
                        "elasticsearch01:9200", "elasticsearch02:9200"]).render()["kibana"]
        self.assertTrue("elasticsearch" in kibana['depends_on'])
        self.assertEqual("elasticsearch01:9200,elasticsearch02:9200", kibana['environment']["ELASTICSEARCH_HOSTS"])

    def test_kibana_port(self):
        kibana = Kibana(version="7.3.0", release=True, kibana_port="1234").render()["kibana"]
        self.assertTrue("127.0.0.1:1234:5601" in kibana['ports'])

    def test_kibana_version(self):
        kibana = Kibana(version="7.3.0", release=True, kibana_version="7.3.0").render()["kibana"]
        self.assertEqual("docker.elastic.co/kibana/kibana:7.3.0", kibana["image"])

    def test_kibana_oss(self):
        kibana = Kibana(version="7.3.0", release=True, kibana_oss=True, kibana_version="7.3.0").render()["kibana"]
        self.assertEqual("docker.elastic.co/kibana/kibana-oss:7.3.0", kibana["image"])

    def test_kibana_snapshot(self):
        kibana = Kibana(version="7.3.0", kibana_snapshot=True, kibana_version="7.3.0").render()["kibana"]
        self.assertEqual("docker.elastic.co/kibana/kibana:7.3.0-SNAPSHOT", kibana["image"])

    def test_kibana_ubi8(self):
        kibana = Kibana(version="7.10.0", release=True, kibana_ubi8=True, kibana_version="7.10.0").render()["kibana"]
        self.assertEqual("docker.elastic.co/kibana/kibana-ubi8:7.10.0", kibana["image"])

    def test_kibana_login_assistance_message(self):
        kibana = Kibana(version="7.6.0", xpack_secure=True, kibana_version="7.6.0").render()["kibana"]
        self.assertIn("Login&#32;details:&#32;`admin/changeme`.",
                      kibana['environment']["XPACK_SECURITY_LOGINASSISTANCEMESSAGE"])
        kibana = Kibana(version="7.6.0", oss=True, xpack_secure=True, kibana_version="7.6.0").render()["kibana"]
        self.assertNotIn("XPACK_SECURITY_LOGINASSISTANCEMESSAGE", kibana['environment'])

    def test_kibana_disable_apm_servicemaps(self):
        kibana = Kibana(version="7.7.0").render()["kibana"]
        self.assertIn("XPACK_APM_SERVICEMAPENABLED", kibana['environment'])

        kibana = Kibana(version="7.7.0", no_kibana_apm_servicemaps=True).render()["kibana"]
        self.assertNotIn("XPACK_APM_SERVICEMAPENABLED", kibana['environment'])

    def test_kibana_login_assistance_message_wihtout_xpack(self):
        kibana = Kibana(version="7.6.0", xpack_secure=False, kibana_version="7.6.0").render()["kibana"]
        self.assertNotIn("XPACK_SECURITY_LOGINASSISTANCEMESSAGE", kibana['environment'])

    def test_kibana_verbose(self):
        kibana = Kibana(version="8.0.0", kibana_verbose=True).render()["kibana"]
        self.assertTrue(kibana['environment']['LOGGING_VERBOSE'])

    def test_kibana_encryption_keys_in_7_6(self):
        kibana = Kibana(version="7.6.0", kibana_version="7.6.0").render()["kibana"]
        self.assertNotIn("XPACK_SECURITY_ENCRYPTIONKEY", kibana['environment'])
        self.assertNotIn("XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY", kibana['environment'])

    def test_kibana_encryption_keys_in_7_7(self):
        kibana = Kibana(version="7.7.0", kibana_version="7.7.0").render()["kibana"]
        self.assertIn("XPACK_SECURITY_ENCRYPTIONKEY", kibana['environment'])
        self.assertIn("XPACK_ENCRYPTEDSAVEDOBJECTS_ENCRYPTIONKEY", kibana['environment'])

    def test_kibana_package_registry_url(self):
        kibana = Kibana(package_registry_url="http://testing.invalid").render()["kibana"]
        self.assertEqual("http://testing.invalid", kibana['environment']['XPACK_FLEET_REGISTRYURL'])

    def test_kibana_yml(self):
        kibana = Kibana(kibana_yml="/path/to.yml").render()["kibana"]
        self.assertIn("/path/to.yml:/usr/share/kibana/config/kibana.yml", kibana['volumes'])


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
            logstash, yaml.safe_load("""
        logstash:
            container_name: localtesting_6.3.0_logstash
            depends_on:
                elasticsearch:
                  condition:
                    service_healthy
            environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200'}
            healthcheck:
                test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://logstash:9600/"]
                timeout: 5s
                interval: 10s
                retries: 12
            image: docker.elastic.co/logstash/logstash:6.3.0
            labels: [co.elastic.apm.stack-version=6.3.0]
            logging:
                driver: json-file
                options: {max-file: '5', max-size: 2m}
            ports: ['127.0.0.1:5044:5044', '9600']
            volumes: ['./docker/logstash/pipeline-6.x-compat/:/usr/share/logstash/pipeline/']""")  # noqa: 501

        )

    def test_logstash_7_3(self):
        logstash = Logstash(version="7.3.0", release=True).render()
        self.assertEqual(
            logstash["logstash"]["volumes"], ['./docker/logstash/pipeline/:/usr/share/logstash/pipeline/']
        )

    def test_logstash_apm_server_7_3(self):
        logstash = Logstash(version="7.1.0", release=True, apm_server_version="7.3.0").render()
        self.assertEqual(
            logstash["logstash"]["volumes"], ['./docker/logstash/pipeline/:/usr/share/logstash/pipeline/']
        )

    def test_logstash_apm_server_snapshot(self):
        logstash = Logstash(version="7.1.0", release=True, apm_server_snapshot="true").render()
        self.assertEqual(
            logstash["logstash"]["volumes"], ['./docker/logstash/pipeline/:/usr/share/logstash/pipeline/']
        )

    def test_logstash_elasticsearch_urls(self):
        logstash = Logstash(version="6.3.5", release=True, logstash_elasticsearch_urls=[
                            "elasticsearch01:9200"]).render()["logstash"]
        self.assertTrue("elasticsearch" in logstash['depends_on'])
        self.assertEqual("elasticsearch01:9200", logstash['environment']["ELASTICSEARCH_URL"])

        logstash = Logstash(version="6.3.5", release=True, logstash_elasticsearch_urls=[
                            "elasticsearch01:9200", "elasticsearch02:9200"]).render()["logstash"]
        self.assertTrue("elasticsearch" in logstash['depends_on'])
        self.assertEqual("elasticsearch01:9200,elasticsearch02:9200", logstash['environment']["ELASTICSEARCH_URL"])

    def test_logstash_ubi8(self):
        logstash = Logstash(version="7.10.0", release=True, ubi8=True).render()["logstash"]
        self.assertEqual("docker.elastic.co/logstash/logstash-ubi8:7.10.0", logstash['image'])


class MetricbeatServiceTest(ServiceTest):
    def test_metricbeat(self):
        metricbeat = Metricbeat(version="7.2.0", release=True, apm_server_pprof_url='apm-server:6060').render()
        self.assertEqual(
            metricbeat, yaml.safe_load("""
                metricbeat:
                    image: docker.elastic.co/beats/metricbeat:7.2.0
                    container_name: localtesting_7.2.0_metricbeat
                    user: root
                    command: ["metricbeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {APM_SERVER_PPROF_HOST: 'apm-server:6060'}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                        kibana:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://localhost:5066/?pretty"]
                        timeout: 5s
                        interval: 10s
                        retries: 12
                    volumes:
                        - ./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml
                        - /var/run/docker.sock:/var/run/docker.sock
                        - ./scripts/tls/ca/ca.crt:/usr/share/beats/config/certs/stack-ca.crt""")
        )

    def test_logstash_output(self):
        beat = Metricbeat(version="6.3.100", metricbeat_output="logstash").render()["metricbeat"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in beat["command"], "{} not set in {} while output=logstash".format(o, beat["command"]))

    def test_metricbeat_elasticsearch_output_tls(self):
        metricbeat = Metricbeat(version="7.8.100", elasticsearch_enable_tls=True).render()["metricbeat"]
        self.assertTrue(
            "output.elasticsearch.ssl.certificate_authorities=['/usr/share/beats/config/certs/stack-ca.crt']" in
            metricbeat["command"],
            "CA not set when elasticsearch TLS is enabled")

    def test_metricbeat_elasticsearch_urls(self):
        beat = Metricbeat(version="6.2.4", release=True, metricbeat_elasticsearch_urls=[
                          "elasticsearch01:9200"]).render()["metricbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue("output.elasticsearch.hosts=[\"elasticsearch01:9200\"]" in beat['command'])

        beat = Metricbeat(version="6.2.4", release=True, metricbeat_elasticsearch_urls=[
                          "elasticsearch01:9200", "elasticsearch02:9200"]).render()["metricbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue(
            "output.elasticsearch.hosts=[\"elasticsearch01:9200\", \"elasticsearch02:9200\"]" in beat['command'])

    def test_apm_server_pprof_url(self):
        beat = Metricbeat(version="6.2.4", release=True, apm_server_pprof_url="apm-server:1234").render()["metricbeat"]
        self.assertEqual("apm-server:1234", beat["environment"]["APM_SERVER_PPROF_HOST"])

    def test_config_6(self):
        beat = Metricbeat(version="6.8.0", release=True, metricbeat_output="logstash").render()["metricbeat"]
        self.assertTrue("xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in beat["command"])
        self.assertTrue(
            "./docker/metricbeat/metricbeat.6.x-compat.yml:/usr/share/metricbeat/metricbeat.yml" in beat["volumes"])

    def test_config_71(self):
        beat = Metricbeat(version="7.1.0", release=True, metricbeat_output="logstash").render()["metricbeat"]
        self.assertTrue("xpack.monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in beat["command"])
        self.assertTrue(
            "./docker/metricbeat/metricbeat.6.x-compat.yml:/usr/share/metricbeat/metricbeat.yml" in beat["volumes"])

    def test_config_post_72(self):
        beat = Metricbeat(version="7.2.0", release=True, metricbeat_output="logstash").render()["metricbeat"]
        self.assertTrue("monitoring.elasticsearch.hosts=[\"http://elasticsearch:9200\"]" in beat["command"])
        self.assertTrue("./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml" in beat["volumes"])


class PacketbeatServiceTest(ServiceTest):
    def test_packetbeat(self):
        packetbeat = Packetbeat(version="7.3.0", release=True).render()
        self.assertEqual(
            packetbeat, yaml.safe_load("""
                packetbeat:
                    image: docker.elastic.co/beats/packetbeat:7.3.0
                    container_name: localtesting_7.3.0_packetbeat
                    user: root
                    command: ["packetbeat", "-e", "--strict.perms=false", "-E", "packetbeat.interfaces.device=eth0", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["http://elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                          condition:
                            service_healthy
                        kibana:
                          condition:
                            service_healthy
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "-k", "--fail", "--silent", "--output", "/dev/null", "http://localhost:5066/?pretty"]
                        timeout: 5s
                        interval: 10s
                        retries: 12
                    volumes:
                        - ./docker/packetbeat/packetbeat.yml:/usr/share/packetbeat/packetbeat.yml
                        - /var/run/docker.sock:/var/run/docker.sock
                        - ./scripts/tls/ca/ca.crt:/usr/share/beats/config/certs/stack-ca.crt
                    network_mode: 'service:apm-server'
                    privileged: true
                    cap_add: ['NET_ADMIN', 'NET_RAW']""")  # noqa: 501
        )

    def test_config_6(self):
        packetbeat = Packetbeat(version="6.2.4", release=True).render()["packetbeat"]
        self.assertTrue("./docker/packetbeat/packetbeat.6.x-compat.yml:/usr/share/packetbeat/packetbeat.yml"
                        in packetbeat["volumes"])

    def test_config_71(self):
        packetbeat = Packetbeat(version="7.1.0", release=True).render()["packetbeat"]
        self.assertTrue("./docker/packetbeat/packetbeat.6.x-compat.yml:/usr/share/packetbeat/packetbeat.yml"
                        in packetbeat["volumes"])

    def test_config_post_72(self):
        packetbeat = Packetbeat(version="7.2.0", release=True).render()["packetbeat"]
        self.assertTrue("./docker/packetbeat/packetbeat.yml:/usr/share/packetbeat/packetbeat.yml"
                        in packetbeat["volumes"])

    def test_packetbeat_elasticsearch_output_tls(self):
        packetbeat = Packetbeat(version="7.8.100", elasticsearch_enable_tls=True).render()["packetbeat"]
        self.assertTrue(
            "output.elasticsearch.ssl.certificate_authorities=['/usr/share/beats/config/certs/stack-ca.crt']" in
            packetbeat["command"],
            "CA not set when elasticsearch TLS is enabled")

    def test_packetbeat_elasticsearch_urls(self):
        beat = Packetbeat(version="6.2.4", release=True,
                          packetbeat_elasticsearch_urls=["elasticsearch01:9200"]).render()["packetbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue("output.elasticsearch.hosts=[\"elasticsearch01:9200\"]" in beat['command'])

        beat = Packetbeat(version="6.2.4", release=True,
                          packetbeat_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                          ).render()["packetbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue(
            "output.elasticsearch.hosts=[\"elasticsearch01:9200\", \"elasticsearch02:9200\"]" in beat['command'])

    def test_packetbeat_with_kibana_username_password(self):
        packetbeat = Packetbeat(packetbeat_kibana_username='foo',
                                packetbeat_kibana_password='bar').render()["packetbeat"]
        self.assertEqual("foo", packetbeat["environment"]["KIBANA_USERNAME"])
        self.assertEqual("bar", packetbeat["environment"]["KIBANA_PASSWORD"])


class HeartbeatServiceTest(ServiceTest):
    def test_heartbeat_elasticsearch_output_tls(self):
        heartbeat = Heartbeat(version="7.8.100", elasticsearch_enable_tls=True).render()["heartbeat"]
        self.assertTrue(
            "output.elasticsearch.ssl.certificate_authorities=['/usr/share/beats/config/certs/stack-ca.crt']" in
            heartbeat["command"],
            "CA not set when elasticsearch TLS is enabled")

    def test_heartbeat_elasticsearch_urls(self):
        beat = Heartbeat(version="6.2.4", release=True,
                         heartbeat_elasticsearch_urls=["elasticsearch01:9200"]).render()["heartbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue("output.elasticsearch.hosts=[\"elasticsearch01:9200\"]" in beat['command'])

        beat = Heartbeat(version="6.2.4", release=True,
                         heartbeat_elasticsearch_urls=["elasticsearch01:9200", "elasticsearch02:9200"]
                         ).render()["heartbeat"]
        self.assertTrue("elasticsearch" in beat['depends_on'])
        self.assertTrue(
            "output.elasticsearch.hosts=[\"elasticsearch01:9200\", \"elasticsearch02:9200\"]" in beat['command'])


class ZookeeperServiceTest(ServiceTest):
    def test_zookeeper(self):
        zookeeper = Zookeeper(version="6.2.4").render()
        self.assertEqual(
            zookeeper, yaml.safe_load("""
                zookeeper:
                    image: confluentinc/cp-zookeeper:latest
                    container_name: localtesting_6.2.4_zookeeper
                    environment:
                        ZOOKEEPER_CLIENT_PORT: 2181
                        ZOOKEEPER_TICK_TIME: 2000
                    ports:
                        - 127.0.0.1:2181:2181""")
        )
