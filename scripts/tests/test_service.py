from __future__ import print_function

import json
import os
import unittest

import yaml

from ..modules.service import Service
from ..modules.aux_services import Logstash, Kafka, Zookeeper
from ..modules.beats import Filebeat, Heartbeat, Metricbeat, Packetbeat
from ..modules.elastic_stack import ApmManaged, ApmServer, ElasticAgent, Elasticsearch, EnterpriseSearch, Kibana, PackageRegistry


class ServiceTest(unittest.TestCase):
    maxDiff = None


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
        self.assertIn("apm-server.auth.api_key.enabled=true", apm_server["command"])

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
        self.assertIn("instrumentation.enabled=true", apm_server["command"])
        self.assertIn("instrumentation.profiling.cpu.enabled=true", apm_server["command"])
        self.assertIn("instrumentation.profiling.heap.enabled=true", apm_server["command"])

        # self instrumentation comes with profiling by default but can be disabled
        apm_server = ApmServer(
            version="8.0.0", apm_server_self_instrument=True, apm_server_profile=False).render()["apm-server"]
        self.assertIn("instrumentation.enabled=true", apm_server["command"])
        self.assertFalse(
            any(e.startswith("instrumentation.profiling") for e in apm_server["command"]),
            "no self profiling settings expected"
        )

        # need self instrumentation enabled to get profiling
        apm_server = ApmServer(
            version="8.0.0", apm_server_self_instrument=False, apm_server_profile=True).render()["apm-server"]
        self.assertNotIn("instrumentation.enabled=true", apm_server["command"])
        self.assertNotIn("instrumentation.profiling.cpu.enabled=true", apm_server["command"])
        self.assertNotIn("instrumentation.profiling.heap.enabled=true", apm_server["command"])

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
                     'apm_server_branch_or_commit': 'main',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_oss(self):
        apm_server = ApmServer(version="6.3.100", apm_server_build="foo.git",
                               release=True, oss=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server-oss:6.3.100',
                     'apm_server_binary': 'apm-server-oss',
                     'apm_server_branch_or_commit': 'main',
                     'apm_server_repo': 'foo.git'},
            'context': 'docker/apm-server'})

    def test_apm_server_build_ubi8(self):
        apm_server = ApmServer(version="7.9.2", apm_server_build="foo.git",
                               release=True, ubi8=True).render()["apm-server"]
        self.assertIsNone(apm_server.get("image"))
        self.assertDictEqual(apm_server["build"], {
            'args': {'apm_server_base_image': 'docker.elastic.co/apm/apm-server-ubi8:7.9.2',
                     'apm_server_binary': 'apm-server',
                     'apm_server_branch_or_commit': 'main',
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

    def test_env_vars(self):
        elasticsearch = Elasticsearch(version="7.3.0", release=True,
            elasticsearch_env_vars=["some.es.env=bar"]).render()["elasticsearch"]
        self.assertIn("some.es.env=bar", elasticsearch['environment'])

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
                        test: ["CMD-SHELL", "curl -s -k http://kibana:5601/api/status | grep -q 'Looking good'"]
                        interval: 10s
                        retries: 30
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
                        test: ["CMD-SHELL", "curl -s -k http://kibana:5601/api/status | grep -q 'Looking good'"]
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

    def test_kibana_env_vars(self):
        kibana = Kibana(version="7.3.0", release=True, kibana_env_vars=["FOO=bar"]).render()["kibana"]
        self.assertIn("FOO", kibana['environment'])

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


class ApmManagedTest(ServiceTest):
    def test_apm_managed(self):
        apm_managed = ApmManaged(version="8.2.0",
                                 release=False,
                                 apm_managed_server_token="foo_token_server",
                                 apm_managed_kibana_token="foo_token_kibana",
                                 apm_managed_elasticsearch_url="http://elasticsearch.example.com:9200",
                                 apm_managed_kibana_url="http://kibana.example.com:5601",
                                 apm_managed_port=8201
                                 ).render()
        self.assertEqual(apm_managed, yaml.safe_load(open('scripts/tests/config/test_apm_managed.yml', 'r')))

    def test_apm_managed_build(self):
        apm_managed = ApmManaged(version="8.2.0",
                                 apm_managed_build="https://github.com/elastic/apm-server.git@foo"
                                 ).render()
        self.assertEqual(apm_managed["apm-server"]["build"], yaml.safe_load(open('scripts/tests/config/test_apm_managed_build.yml', 'r')))

    def test_apm_managed_build(self):
        apm_managed = ApmManaged(version="8.2.0",
                                 apm_managed_build="https://github.com/elastic/apm-server.git@foo"
                                 ).render()
        self.assertEqual(apm_managed["apm-server"]["build"], yaml.safe_load(open('scripts/tests/config/test_apm_managed_build.yml', 'r')))

    def test_apm_managed_security(self):
        kibana = Kibana(version="8.2.0",
                            apm_server_secret_token="foo",
                            apm_server_enable_tls=True,
                            apm_server_url="https://apm-serve.example.comr:8200"
                            ).render()
        self.assertEqual(kibana["kibana"]["environment"]["ELASTIC_APM_SECRET_TOKEN"], "foo")
        self.assertEqual(kibana["kibana"]["environment"]["ELASTIC_APM_TLS"], "true")
        self.assertEqual(kibana["kibana"]["environment"]["ELASTIC_APM_SERVER_URL"], "https://apm-serve.example.comr:8200")
