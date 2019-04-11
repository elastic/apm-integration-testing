#!/usr/bin/env python
import pytest
import json
import subprocess
from tests.fixtures.transactions import minimal
from tests.fixtures.apm_server import apm_server
from tests.fixtures.es import es
from tests.fixtures.kibana import kibana
from tests.fixtures.agents import flask
from tests.fixtures.agents import django
from tests.fixtures.agents import express
from tests.fixtures.agents import rails
from tests.fixtures.agents import go_nethttp
from tests.fixtures.agents import java_spring
from tests.fixtures.agents import rum


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_logreport(report):
    yield
    name = report.nodeid.split(":", 2)[-1]
    subprocess.call(['elasticdump',
                     '--input=http://elasticsearch:9200/apm-*',
                     '--output=/app/tests/results/data-{}.json'.format(name)], shell=True)
    subprocess.call(['elasticdump',
                     '--input=http://elasticsearch:9200/packetbeat-*',
                     '--output=/app/tests/results/packetbeat-{}.json'.format(name)], shell=True)

    if report.when == "call" and report.failed:
        rs = es().es.search(index="apm-*", size=10000)
        try:
            with open("/app/tests/results/data-b-{}.json".format(name), 'w') as outFile:
                json.dump(rs, outFile, sort_keys=True, indent=4, ensure_ascii=False)
        except IOError:
            pass

