# -*- coding: utf-8 -*-

# Licensed to Elasticsearch B.V. under one or more contributor
# license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations

"""
Tests for Dyno control plane
"""
import pytest
from dyno import app

@pytest.fixture(scope="session")
def app():
    """
    This overrides the app() function to initialize the pytest-flask
    plugin. For more information, please see the pytest-flask
    documentation:

    https://pytest-flask.readthedocs.io
    """
    dyno_app = app.create_app(app_env='test')
    return dyno_app

@pytest.fixture
def toxi_default_environment(monkeypatch):
    """
    Set up default variables to produce a functional
    toxi environment
    """
    monkeypatch.setenv("TOXI_HOST", "dummy_toxi_host")
    monkeypatch.setenv("TOXI_PORT", "1648")
