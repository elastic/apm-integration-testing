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
Tests for the Openbeans Dyno Docker integration
"""
from pytest import mark, raises
from unittest import mock
from flask import url_for
import dyno.app.api.docker as dkr

CONTAINER_NAME_FUZZ = ['a_foo', 'b__foo', '_c_foo']

@mark.parametrize('container_fuzz', CONTAINER_NAME_FUZZ)
@mock.patch('dyno.app.api.docker.container_list', return_value={'containers': CONTAINER_NAME_FUZZ})
def test_normalize_name_multiple(cl, container_fuzz):
    """
    GIVEN multiple containers with names which end in `foo`
    WHEN the name ending in `foo` is passed into the _normalize_name function
    THEN function raises an exception
    """
    with raises(Exception, match="more than one"):
        dkr._normalize_name('foo')


@mock.patch('dyno.app.api.docker.container_list', return_value={'containers': CONTAINER_NAME_FUZZ})
def test_normalize_name_multiple_not_found(cl):
    """
    GIVEN no containers which end in `baz`
    WHEN a name ending in `baz` if passed into the _normalize_name func
    THEN an exception is raised
    """
    with raises(Exception, match="not found"):
        dkr._normalize_name('baz')

@mock.patch('dyno.app.api.docker.client')
def test_list(docker_mock, client):
    """
    GIVEN an HTTP call to /docker/list
    WHEN the results are returned
    THEN the results contain a list of running containers
    """
    fake_container = mock.Mock()
    fake_container.name = 'fake_container'
    list_mock = mock.Mock(return_value=[fake_container], name='list_mock')
    docker_mock.containers.list = list_mock
    ret = client.get(url_for('docker.container_list'))
    assert ret.json == {'containers': ['fake_container']}

@mock.patch('dyno.app.api.docker._normalize_name', return_value='fake_container_name')
def test_query(fake_container_patch, docker_inspect, client):
    """
    GIVEN an HTTP call to /docker/query
    WHEN the results are returned
    THEN the results container info about the CPU and memory
    """
    with mock.patch.object(dkr.low_client, 'inspect_container', return_value=docker_inspect):
        ret = client.get(url_for('docker.query'), query_string={'c': 'fake_container_name'})
        assert ret.json['CPU'] == 1000
        assert ret.json['Mem'] == 200

@mock.patch('dyno.app.api.docker.client', name='docker_mock')
@mock.patch('dyno.app.api.docker._normalize_name', return_value='fake_container_name', name='normalize_mock')
def test_update(fake_container_patch, docker_mock, client):
    """
    GIVEN an HTTP call to /docker/update
    WHEN the call contains settings to be updated
    THEN the settings are updated
    """
    fake_container = mock.Mock(name='fake_container')
    fake_container.name = 'fake_container'
    get_mock = mock.Mock(return_value=fake_container, name='get_mock')
    docker_mock.containers.get = get_mock
    client.get(url_for('docker.update'), query_string={'c': 'opbeans-python', 'component': 'CPU', 'val': 100})

    fake_container.update.assert_called_with(cpu_quota=25990)

# FIXME This is marked as xfail pending a centralization of the normalization functions
@mark.xfail
@mark.parametrize('val', range(1,101, 10))
@mock.patch('dyno.app.api.control._range', mock.Mock(return_value={'Fr': [1,10]}))
def test_normalize(val):
    """
    GIVEN values between 1-100
    WHEN the value is sent to be normalized
    THEN the correct normalized value is returned
    """
    got = dkr._normalize_value('cpu', val)
    want = (101 - val) / 10
    assert got == want

# FIXME This is marked as xfail pending a centralization of the normalization functions
@mark.xfail
@mark.parametrize('val', range(1,10))
@mock.patch('dyno.app.api.control._range', mock.Mock(return_value={'Fr': [1,10]}))
def test_denormalize(val):
    """
    GIVEN values between 1-100
    WHEN the value is sent to be denormalized
    THEN the correct normalized value is returned
    """
    got = dkr._denormalize_value('cpu', val)
    want = 100 - (val * 10)
    assert got == want
