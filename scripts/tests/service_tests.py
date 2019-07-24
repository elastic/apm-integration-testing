from __future__ import print_function

import unittest
import json
import yaml

from ..compose import (AgentDotnet, AgentGoNetHttp, AgentJavaSpring, AgentNodejsExpress,
                       AgentPythonDjango, AgentPythonFlask, AgentRubyRails)

from ..compose import (ApmServer, Kibana, Elasticsearch, Filebeat, Metricbeat,
                       Packetbeat, Logstash, Kafka)

from ..compose import Zookeeper


class ServiceTest(unittest.TestCase):
    maxDiff = None


class AgentServiceTest(ServiceTest):
    def test_agent_go_net_http(self):
        agent = AgentGoNetHttp().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-go-net-http:
                    build:
                        args:
                            GO_AGENT_BRANCH: master
                            GO_AGENT_REPO: elastic/apm-agent-go
                        dockerfile: Dockerfile
                        context: docker/go/nethttp
                    container_name: gonethttpapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_FLUSH_INTERVAL: 500ms
                        ELASTIC_APM_SERVICE_NAME: gonethttpapp
                        ELASTIC_APM_TRANSACTION_IGNORE_NAMES: healthcheck
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://gonethttpapp:8080/healthcheck"]
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

    def test_agent_nodejs_express(self):
        agent = AgentNodejsExpress().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-nodejs-express:
                    build:
                        dockerfile: Dockerfile
                        context: docker/nodejs/express
                    container_name: expressapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    command: bash -c "npm install elastic-apm-node && node app.js"
                    environment:
                        EXPRESS_SERVICE_NAME: expressapp
                        EXPRESS_PORT: "8010"
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://expressapp:8010/healthcheck"]
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

    def test_agent_python_django(self):
        agent = AgentPythonDjango().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-python-django:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/django
                    command: bash -c "pip install -q -U elastic-apm && python testapp/manage.py runserver 0.0.0.0:8003"
                    container_name: djangoapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    environment:
                        DJANGO_SERVICE_NAME: djangoapp
                        DJANGO_PORT: 8003
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://djangoapp:8003/healthcheck"]
                    ports:
                        - 127.0.0.1:8003:8003
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentPythonDjango(apm_server_url="http://foo").render()["agent-python-django"]
        self.assertEqual("http://foo", agent["environment"]["APM_SERVER_URL"], agent)

    def test_agent_python_flask(self):
        agent = AgentPythonFlask(version="6.2.4").render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-python-flask:
                    build:
                        dockerfile: Dockerfile
                        context: docker/python/flask
                    command: bash -c "pip install -q -U elastic-apm && gunicorn app:app"
                    container_name: flaskapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    environment:
                        FLASK_SERVICE_NAME: flaskapp
                        GUNICORN_CMD_ARGS: "-w 4 -b 0.0.0.0:8001"
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://flaskapp:8001/healthcheck"]
                    ports:
                        - 127.0.0.1:8001:8001
            """)  # noqa: 501
        )

        # test overrides
        agent = AgentPythonFlask(apm_server_url="http://foo").render()["agent-python-flask"]
        self.assertEqual("http://foo", agent["environment"]["APM_SERVER_URL"])

    def test_agent_ruby_rails(self):
        agent = AgentRubyRails().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-ruby-rails:
                    build:
                        args:
                            RUBY_AGENT_VERSION: latest
                            RUBY_AGENT_REPO: elastic/apm-agent-ruby
                        dockerfile: Dockerfile
                        context: docker/ruby/rails
                    container_name: railsapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    command: bash -c "bundle install && RAILS_ENV=production bundle exec rails s -b 0.0.0.0 -p 8020"
                    environment:
                        APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_SERVER_URL: http://apm-server:8200
                        ELASTIC_APM_SERVICE_NAME: railsapp
                        RAILS_SERVICE_NAME: railsapp
                        RAILS_PORT: 8020
                        RUBY_AGENT_VERSION: latest
                        RUBY_AGENT_VERSION_STATE: release
                        RUBY_AGENT_REPO: elastic/apm-agent-ruby
                    healthcheck:
                        interval: 10s
                        retries: 60
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://railsapp:8020/healthcheck"]
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

    def test_agent_java_spring(self):
        agent = AgentJavaSpring().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-java-spring:
                    build:
                        args:
                            JAVA_AGENT_BRANCH: master
                            JAVA_AGENT_BUILT_VERSION: ""
                            JAVA_AGENT_REPO: elastic/apm-agent-java
                        dockerfile: Dockerfile
                        context: docker/java/spring
                    container_name: javaspring
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_SERVICE_NAME: springapp
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output",
                        "/dev/null", "http://javaspring:8090/healthcheck"]
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

    def test_agent_dotnet(self):
        agent = AgentDotnet().render()
        self.assertDictEqual(
            agent, yaml.load("""
                agent-dotnet:
                    build:
                        args:
                            DOTNET_AGENT_BRANCH: master
                            DOTNET_AGENT_VERSION: ""
                            DOTNET_AGENT_REPO: elastic/apm-agent-dotnet
                        dockerfile: Dockerfile
                        context: docker/dotnet
                    container_name: dotnetapp
                    depends_on:
                        apm-server:
                            condition: 'service_healthy'
                    environment:
                        ELASTIC_APM_API_REQUEST_TIME: '3s'
                        ELASTIC_APM_FLUSH_INTERVAL: '5'
                        ELASTIC_APM_SAMPLE_RATE: '1'
                        ELASTIC_APM_SERVICE_NAME: dotnetapp
                        ELASTIC_APM_TRANSACTION_IGNORE_NAMES: 'healthcheck'
                    healthcheck:
                        interval: 10s
                        retries: 12
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output",
                        "/dev/null", "http://dotnetapp:8100/healthcheck"]
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

    def test_logstash_output(self):
        apm_server = ApmServer(version="6.3.100", apm_server_output="logstash").render()["apm-server"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]",
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
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]" in apm_server["command"],
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
            return yaml.load(setting)

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
                {"file": {"path": "$${path.data}/spool.dat"}, "write":{"flush.timeout": "0s"}},
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

    def test_apm_server_build_branch(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git@bar", release=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server:6.3.100',
                     'apm_server_branch_or_commit': 'bar',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_branch_default(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git", release=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server:6.3.100',
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

    def test_apm_server_tee(self):
        render = ApmServer(version="6.4.100", apm_server_count=2, apm_server_tee=True).render()
        apm_server_lb = render["apm-server"]
        apm_server_2 = render["apm-server-2"]
        self.assertIn("build", apm_server_lb)
        self.assertDictEqual(apm_server_lb["build"], {"context": "docker/apm-server/teeproxy"})
        self.assertListEqual(["127.0.0.1:8200:8200"], apm_server_lb["ports"], apm_server_lb["ports"])
        self.assertListEqual(["8200", "6060"], apm_server_2["ports"], apm_server_2["ports"])

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
                        "APM Server Kbana enabled by default")
        self.assertTrue("apm-server.kibana.host=kibana:5601" in apm_server["command"],
                        "APM Server Kibana host set by default")

        apm_server = ApmServer(version="7.3", apm_server_acm_disable=True).render()["apm-server"]
        self.assertTrue("apm-server.kibana.enabled=false" in apm_server["command"],
                        "APM Server Kibana disabled when apm_server_disable_kibana=True")


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


class FilebeatServiceTest(ServiceTest):
    def test_filebeat_pre_6_1(self):
        filebeat = Filebeat(version="6.0.4", release=True).render()
        self.assertEqual(
            filebeat, yaml.load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.0.4
                    container_name: localtesting_6.0.4_filebeat
                    user: root
                    command: ["filebeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/filebeat/filebeat.simple.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )

    def test_filebeat_post_6_1(self):
        filebeat = Filebeat(version="6.1.1", release=True).render()
        self.assertEqual(
            filebeat, yaml.load("""
                filebeat:
                    image: docker.elastic.co/beats/filebeat:6.1.1
                    container_name: localtesting_6.1.1_filebeat
                    user: root
                    command: ["filebeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml
                        - /var/lib/docker/containers:/var/lib/docker/containers
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )

    def test_logstash_output(self):
        beat = Filebeat(version="6.3.100", filebeat_output="logstash").render()["filebeat"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in beat["command"], "{} not set in {} while output=logstash".format(o, beat["command"]))


class KafkaServiceTest(ServiceTest):
    def test_kafka(self):
        kafka = Kafka(version="6.2.4").render()
        self.assertEqual(
            kafka, yaml.load("""
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
            kibana, yaml.load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana-x-pack:6.2.4
                    container_name: localtesting_6.2.4_kibana
                    environment:
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_URL: http://elasticsearch:9200
                        XPACK_MONITORING_ENABLED: 'true'
                    ports:
                        - "127.0.0.1:5601:5601"
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    healthcheck:
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://kibana:5601/api/status"]
                        interval: 10s
                        retries: 20
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                    labels:
                        - co.elastic.apm.stack-version=6.2.4""")  # noqa: 501
        )

    def test_6_3_release(self):
        kibana = Kibana(version="6.3.5", release=True).render()
        self.assertDictEqual(
            kibana, yaml.load("""
                kibana:
                    image: docker.elastic.co/kibana/kibana:6.3.5
                    container_name: localtesting_6.3.5_kibana
                    environment:
                        SERVER_NAME: kibana.example.org
                        ELASTICSEARCH_URL: http://elasticsearch:9200
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
                        test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://kibana:5601/api/status"]
                        interval: 10s
                        retries: 20
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                    labels:
                        - co.elastic.apm.stack-version=6.3.5""")  # noqa: 501
        )


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
            logstash, yaml.load("""
        logstash:
            container_name: localtesting_6.3.0_logstash
            depends_on:
                elasticsearch: {condition: service_healthy}
            environment: {ELASTICSEARCH_URL: 'http://elasticsearch:9200'}
            healthcheck:
                test: ["CMD", "curl", "--write-out", "'HTTP %{http_code}'", "--fail", "--silent", "--output", "/dev/null", "http://logstash:9600/"]
                interval: 10s
                retries: 12
            image: docker.elastic.co/logstash/logstash:6.3.0
            labels: [co.elastic.apm.stack-version=6.3.0]
            logging:
                driver: json-file
                options: {max-file: '5', max-size: 2m}
            ports: ['127.0.0.1:5044:5044', '9600']
            volumes: ['./docker/logstash/pipeline/:/usr/share/logstash/pipeline/']""")  # noqa: 501

        )


class MetricbeatServiceTest(ServiceTest):
    def test_metricbeat(self):
        metricbeat = Metricbeat(version="6.2.4", release=True).render()
        self.assertEqual(
            metricbeat, yaml.load("""
                metricbeat:
                    image: docker.elastic.co/beats/metricbeat:6.2.4
                    container_name: localtesting_6.2.4_metricbeat
                    user: root
                    command: ["metricbeat", "-e", "--strict.perms=false", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/metricbeat/metricbeat.yml:/usr/share/metricbeat/metricbeat.yml
                        - /var/run/docker.sock:/var/run/docker.sock""")
        )

    def test_logstash_output(self):
        beat = Metricbeat(version="6.3.100", metricbeat_output="logstash").render()["metricbeat"]
        options = [
            "output.elasticsearch.enabled=false",
            "output.logstash.enabled=true",
            "output.logstash.hosts=[\"logstash:5044\"]",
            "xpack.monitoring.elasticsearch.hosts=[\"elasticsearch:9200\"]",
        ]
        for o in options:
            self.assertTrue(o in beat["command"], "{} not set in {} while output=logstash".format(o, beat["command"]))


class PacketbeatServiceTest(ServiceTest):
    def test_packetbeat(self):
        packetbeat = Packetbeat(version="6.2.4", release=True).render()
        self.assertEqual(
            packetbeat, yaml.load("""
                packetbeat:
                    image: docker.elastic.co/beats/packetbeat:6.2.4
                    container_name: localtesting_6.2.4_packetbeat
                    user: root
                    command: ["packetbeat", "-e", "--strict.perms=false", "-E", "packetbeat.interfaces.device=eth0", "-E", "setup.dashboards.enabled=true", "-E", 'output.elasticsearch.hosts=["elasticsearch:9200"]', "-E", "output.elasticsearch.enabled=true"]
                    environment: {}
                    logging:
                        driver: 'json-file'
                        options:
                            max-size: '2m'
                            max-file: '5'
                    depends_on:
                        elasticsearch:
                            condition: service_healthy
                        kibana:
                            condition: service_healthy
                    volumes:
                        - ./docker/packetbeat/packetbeat.yml:/usr/share/packetbeat/packetbeat.yml
                        - /var/run/docker.sock:/var/run/docker.sock
                    network_mode: 'service:apm-server'
                    privileged: 'true'
                    cap_add: ['NET_ADMIN', 'NET_RAW']""") # noqa: 501
        )


class ZookeeperServiceTest(ServiceTest):
    def test_zookeeper(self):
        zookeeper = Zookeeper(version="6.2.4").render()
        self.assertEqual(
            zookeeper, yaml.load("""
                zookeeper:
                    image: confluentinc/cp-zookeeper:latest
                    container_name: localtesting_6.2.4_zookeeper
                    environment:
                        ZOOKEEPER_CLIENT_PORT: 2181
                        ZOOKEEPER_TICK_TIME: 2000
                    ports:
                        - 127.0.0.1:2181:2181""")
        )
