#!/usr/bin/env python
import pytest
from tests.fixtures.transactions import minimal
from tests.fixtures.apm_server import apm_server
from tests.fixtures.elasticsearch import elasticsearch
from tests.fixtures.kibana import kibana
from tests.fixtures.agents import flask
from tests.fixtures.agents import flask_gunicorn
from tests.fixtures.agents import django
from tests.fixtures.agents import express
