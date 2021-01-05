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


