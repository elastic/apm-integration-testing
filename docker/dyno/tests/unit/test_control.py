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
import toxiproxy
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

def test_get_app(fetch_proxy_mock, client):
    """
    GIVEN an HTTP client
    WHEN that client requests the /app endpoint
    THEN the client receives a dictionary containing the app proxy config
    """
    with mock.patch('dyno.app.api.control._fetch_proxy', fetch_proxy_mock):
        res = client.get(url_for('api.fetch_app'), query_string={'name': 'fake_proxy'})
        assert res.json == {
                'enabled': True,
                'listen': 8080,
                'name': 'opbeans-proxy',
                'toxics': {},
                'upstream': 'fake_upstream'
                }

def test_get_apps(fetch_proxy_mock, client):
    """
    GIVEN an HTTP client
    WHEN that client requests the /apps endpoint
    THEN the client receives a dictionary containing a list of configured apps
    """
    with mock.patch('dyno.app.api.control._fetch_proxy', fetch_proxy_mock):
        res = client.get(url_for('api.fetch_all_apps'), query_string={'name': 'fake_proxy'})
        assert res.json == {'proxies': ['fake_proxy']}

def test_get_apps_full(fetch_proxy_mock, client):
    """
    GIVEN an HTTP client
    WHEN that client requests the /apps endpoint with the `full` argument supplied
    THEN the client receives a dictionary back with all apps and their configurations
    """
    with mock.patch('dyno.app.api.control._fetch_proxy', fetch_proxy_mock):
        res = client.get(
                url_for('api.fetch_all_apps'),
                query_string={'name': 'fake_proxy', 'full': True}
                )
        assert res.json == {'proxies': [{'listen': 8080, 'name': 'opbeans-proxy'}]}

def test_enable(client):
    """
    GIVEN an HTTP client
    WHEN that client requests the /enable endpoint to enable a given proxy
    THEN the toxiproxy API is instructed to enable the proxy
    """
    t_ = mock.Mock(spec=toxiproxy.Toxiproxy, name='toxi_mock')
    enable_mock = mock.Mock(spec=toxiproxy.proxy.Proxy, name='enable_mock')
    t_.attach_mock(mock.Mock(name='get_proxy_mock', return_value=enable_mock), 'get_proxy')
    with mock.patch('dyno.app.api.control._fetch_proxy', return_value=t_):
        with mock.patch('toxiproxy.proxy.Proxy', enable_mock):
            client.get(url_for('api.enable_proxy'))
            enable_mock.enable.assert_called()

def test_disable(client):
    """
    GIVEN an HTTP client
    WHEN that client requests the /disable endpoint to enable a given proxy
    THEN the toxiproxy API is instructed to disable the proxy
    """
    t_ = mock.Mock(spec=toxiproxy.Toxiproxy)
    disable_mock = mock.Mock(spec=toxiproxy.proxy.Proxy)
    t_.attach_mock(mock.Mock(name='get_proxy_mock', return_value=disable_mock), 'get_proxy')
    with mock.patch('dyno.app.api.control._fetch_proxy', return_value=t_):
        with mock.patch('toxiproxy.proxy.Proxy', disable_mock):
            client.get(url_for('api.disable_proxy'))
            disable_mock.disable.assert_called()

@mark.parametrize('toxi_code', ctl.toxic_map.keys())
def test_slide(toxi_code, client):
    """
    GIVEN an HTTP client
    WHEN that client hits the /slider endpoint to adjust values for a proxy
    THEN the proxy values are adjusted
    """
    t_ = mock.Mock(spec=toxiproxy.Toxiproxy)
    proxy_mock = mock.Mock(spec=toxiproxy.proxy.Proxy)
    t_.attach_mock(mock.Mock(name='get_proxy_mock', return_value=proxy_mock), 'get_proxy')
    with mock.patch('dyno.app.api.control._fetch_proxy', return_value=t_):
        with mock.patch('toxiproxy.proxy.Proxy', proxy_mock):
            client.post(url_for('api.slide'), json={'tox_code': toxi_code, 'val': 100})
            proxy_mock.add_toxic.assert_called()

@mark.parametrize('toxi_code', ctl.toxic_map.keys())
def test_slide_exception_side_effect(toxi_code, client):
    """
    GIVEN an HTTP client
    WHEN that client hits the /slider endpoint to adjust values for a proxy
    THEN the proxy values are adjusted
    """
    t_ = mock.Mock(spec=toxiproxy.Toxiproxy)
    proxy_mock = mock.Mock(spec=toxiproxy.proxy.Proxy)
    proxy_mock.toxics = mock.Mock(return_value=['fake_proxy_1', 'fake_proxy_2'])
    proxy_mock.add_toxic = mock.Mock(side_effect=Exception, name='sider')
    t_.attach_mock(mock.Mock(name='get_proxy_mock', return_value=proxy_mock), 'get_proxy')
    with mock.patch('dyno.app.api.control._fetch_proxy', return_value=t_):
        with mock.patch('toxiproxy.proxy.Proxy', proxy_mock):
            client.post(url_for('api.slide'), json={'tox_code': toxi_code, 'val': 100})
            proxy_mock.add_toxic.assert_called()
            proxy_mock.destroy_toxic.assert_called()

@mark.parametrize('val', range(1,101, 10))
@mock.patch('dyno.app.api.control._range', mock.Mock(return_value={'Fr': [1,10]}))
def test_normalize(val):
    """
    GIVEN values between 1-100
    WHEN the value is sent to be normalized
    THEN the correct normalized value is returned
    """
    got = ctl._normalize_value('Fr', val)
    want = (101 - val) / 10
    assert got == want

@mark.parametrize('val', range(1,10))
@mock.patch('dyno.app.api.control._range', mock.Mock(return_value={'Fr': [1,10]}))
def test_denormalize(val):
    """
    GIVEN values between 1-100
    WHEN the value is sent to be denormalized
    THEN the correct normalized value is returned
    """
    got = ctl._denormalize_value('Fr', val)
    want = 100 - (val * 10)
    assert got == want
