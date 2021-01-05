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
import toxiproxy
import pytest
import dyno

from unittest import mock

@pytest.fixture(scope="session")
def app():
    """
    This overrides the app() function to initialize the pytest-flask
    plugin. For more information, please see the pytest-flask
    documentation:

    https://pytest-flask.readthedocs.io
    """
    dyno_app = dyno.app.create_app()
    return dyno_app

@pytest.fixture
def toxi_default_environment(monkeypatch):
    """
    Set up default variables to produce a functional
    toxi environment
    """
    monkeypatch.setenv("TOXI_HOST", "dummy_toxi_host")
    monkeypatch.setenv("TOXI_PORT", "1648")

@pytest.fixture
def fetch_proxy_mock():
    # Put the Toxiproxy mock into a container mock for use in 
    return mock.MagicMock(return_value=toxi_mock())


@pytest.fixture
def toxi():
    return toxi_mock()

#@pytest.fixture
def toxi_mock():
    """
    Represent a set of proxied services
    """
    # Create the mock that we'll ultimately return
    toxi_mock = mock.patch('toxiproxy.server.Toxiproxy', autospec=True)
    # Create the mock that we'll use to represent a Proxy
    #p = toxiproxy.Proxy(name='opbeans-proxy', enabled= True, listen=8080, upstream='fake_upstream') 
    p = mock.patch('toxiproxy.Proxy', autospec=True)
    p.name = 'opbeans-proxy'
    p.enabled = True
    p.listen = 8080
    p.upstream = 'fake_upstream'
    # Create the mock that we'll use to represent containers for a Toxic
    #toxic = toxiproxy.toxic.Toxic(type='fake_toxic_type', name='fake_toxic')
    toxic = mock.patch('toxiproxy.toxic.Toxic', autospec=True)
    toxic.type='fake_toxic_type'
    toxic.name='fake_toxic'
    toxic.attributes = {}
    # Create the mock to represent the toxic itself
    toxic_mock = mock.MagicMock(return_value={'fake_toxic_ob': toxic})

    # Overlay the raw toxic as a return for the .toxics() function
    p.toxics = toxic_mock
    # Overlay a dictionary as a return for the .proxies() function to Toxiproxy
    toxi_mock.proxies = lambda: {'fake_proxy': p}
    # Put the Toxiproxy mock into a container mock for use in 
    #fetch_proxy_mock = mock.MagicMock(return_value=toxi_mock)

    #return fetch_proxy_mock
    return toxi_mock
