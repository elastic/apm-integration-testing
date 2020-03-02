#!/usr/bin/env python
import os
import sys
import pytest
import subprocess

from tests.fixtures.transactions import minimal
from tests.fixtures.apm_server import apm_server
from tests.fixtures.es import es
from tests.fixtures.kibana import kibana
from tests.fixtures.agents import flask
from tests.fixtures.agents import django
from tests.fixtures.agents import dotnet
from tests.fixtures.agents import express
from tests.fixtures.agents import rails
from tests.fixtures.agents import go_nethttp
from tests.fixtures.agents import java_spring
from tests.fixtures.agents import rum
from tests.fixtures import default
from tests.utils import getElasticsearchURL


def pytest_addoption(parser):
    parser.addoption(
        "--run-upgrade", action="store_true", default=False, help="run upgrade tests"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-upgrade"):
        return
    skip_upgrade = pytest.mark.skip(reason="need --run-upgrade option to run")
    for item in items:
        if item.get_marker("upgradetest"):
            item.add_marker(skip_upgrade)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_logreport(report):
    yield
    if report.when == "call" and report.failed:
        name = report.nodeid.split(":", 2)[-1]
        try:
            es_url = getElasticsearchURL()
            isDumpEnable = os.getenv("ENABLE_ES_DUMP")
            if isDumpEnable is not None:
                subprocess.call(['elasticdump',
                                 '--input={}/apm-*'.format(es_url),
                                 '--output=/app/tests/results/data-{}.json'.format(name)])
                subprocess.call(['elasticdump',
                                 '--input={}/packetbeat-*'.format(es_url),
                                 '--output=/app/tests/results/packetbeat-{}.json'.format(name)])
        except IOError:
            sys.stderr.write("Error launching elasticdump")
            pass
