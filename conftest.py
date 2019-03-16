#!/usr/bin/env python
import pytest
import json
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
def pytest_runtest_teardown(item, nextitem):
    """Called after pytest_runtest_call."""
    outcome = yield
    rs = es().es.search(index="apm-*")
    with open(f'/app/tests/results/data-{item.name}.json', 'w') as outFile:
        json.dump(rs, outFile, sort_keys=True, indent=4, ensure_ascii=False)
