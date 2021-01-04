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
Tests for the Openbeans Dyno
"""
from pytest import mark
from unittest import mock
from flask import url_for
import dyno.app.api.control as ctl

@mock.patch('toxiproxy.server.Toxiproxy.update_api_consumer')
def test_fetch_proxy_update_consumer(consumer_patch, toxi_default_environment):
    """
    GIVEN an environment with TOXI_HOST or TOXI_PORT set
    WHEN the _fetch_proxy() helper function is called
    THEN the proxy api consumer is updated
    """
    ctl._fetch_proxy()
    consumer_patch.assert_called_once()


@mark.parametrize('toxi_env', ['TOXI_HOST', 'TOXI_PORT'])
@mock.patch('toxiproxy.server.Toxiproxy.update_api_consumer')
def test_fetch_proxy_no_update_consumer(consumer_patch, toxi_default_environment, toxi_env, monkeypatch):
    """
    GIVEN an environment without both TOXI_HOST and TOXI_PORT set
    WHEN the _fetch_proxy() helper function is called
    THEN the proxy api consumer is *not* updated
    """
    monkeypatch.delenv(toxi_env)
    ctl._fetch_proxy()
    consumer_patch.assert_not_called()

@mark.parametrize('toxi_code', ctl.toxic_map.keys())
def test_decode_toxi(toxi_code):
    """
    GIVEN an shortned toxic code
    WHEN the code is given to the _decode_toxic() function
    THEN it receives back dictionary with the code
    """
    assert ctl._decode_toxic(toxi_code)

@mark.parametrize('toxi_cfg', ctl.toxic_map.values())
def test_encode_toxi(toxi_cfg):
    """
    GIVEN a toxi configuration
    WHEN that configuration is passed to the _encode_toxic() function
    THEN the code for that configuration is returned
    """
    assert ctl._encode_toxic(toxi_cfg['type'], toxi_cfg['attr'])

def test_get_app(toxi_mock, client):
    with mock.patch('dyno.app.api.control._fetch_proxy', toxi_mock):
        res = client.get(url_for('api.fetch_app'), query_string={'name': 'fake_proxy'})
        assert res.json == {'enabled': True, 'listen': 8080, 'name': 'opbeans-proxy', 'toxics': {}, 'upstream': 'fake_upstream'}

def test_get_apps(toxi_mock, client):
    with mock.patch('dyno.app.api.control._fetch_proxy', toxi_mock):
        res = client.get(url_for('api.fetch_all_apps'), query_string={'name': 'fake_proxy'})
        assert res.json == {'proxies': ['fake_proxy']}
