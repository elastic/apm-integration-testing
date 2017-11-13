import pytest
from fixtures.transactions import minimal
from fixtures.apm_server import apm_server
from fixtures.dependencies import elasticsearch
from fixtures.dependencies import kibana
from fixtures.agents import flask
from fixtures.agents import flask_gunicorn
from fixtures.agents import django
from fixtures.agents import express
import subprocess
import os


@pytest.fixture(scope="session", autouse=True)
def finalizer():
    yield
    if os.environ.get('NETWORK') is None:
        os.environ['NETWORK'] = 'apm_test'
    script = './tests/fixtures/setup/stop_docker.sh'
    subprocess.call([script])
