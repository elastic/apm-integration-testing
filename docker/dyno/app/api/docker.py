# -*- coding: utf-8 -*-
#
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

import os
import docker
import yaml
from dyno import app
from flask import request

from flask import Blueprint

bp = Blueprint('docker', __name__)


client = docker.from_env()
low_client = docker.APIClient()


def _normalize_name(name):
    """
    Small helper to find the container name.

    Pass in something like `elasticsearch` and have to
    find it in a list of container names that are like:
    localtesting_7.9.0_elasticsearch

    Parameters
    ----------
    str : name
        The name to normalize

    Returns
    -------
    str
        The normalized name
    """
    containers = container_list()
    found = []
    for container in containers['containers']:
        if container.split('_').pop().strip() == name:
            found.append(container)
    if len(found) > 1:
        raise Exception('Found more than one instance matching [{}]'.format(name))
    if not found:
        raise Exception('Could not normalize [{}] because it was not found in the container list')
    return found[0]


@bp.route('/list', methods=['GET'])
def container_list():
    """
    Return list of containers

    Note
    ----
    Exposed via HTTP at /api/docker/list

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Returns
    -------
    dict
        A dict with a key of 'containers' and the value of which is a list of
        the running containers

    Examples
    --------
	❯ curl -s http://localhost:9000/api/docker/list|jq
    {
      "containers": [
        "localtesting_8.0.0_opbeans-load-generator",
        "localtesting_latest_opbeans-python",
        "localtesting_latest_opbeans-python01",
        "dyno",
        "localtesting_8.0.0_apm-server",
        "localtesting_8.0.0_kibana",
        "localtesting_8.0.0_elasticsearch",
        "localtesting_8.0.0_postgres",
        "localtesting_8.0.0_redis",
        "localtesting_8.0_toxi",
        "localtesting_8.0_stats-d"
      ]
    }
    """
    ret = {'containers': []}
    containers = client.containers.list()
    for container in containers:
        ret['containers'].append(container.name)
    return ret


@bp.route('/query', methods=['GET'])
def query():
    """
    Inspect container and return information

    Note
    ----
    Exposed via HTTP at /api/docker/query

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    c : str
        Container to get

    Returns
    -------
    dict
        A dictionary showing the configuration for the running container

    """
    container = request.args.get('c')
    config = low_client.inspect_container(_normalize_name(container))['HostConfig']
    """
    cpu_quota (int) - Limit CPU CFS (Completely Fair Scheduler) quota
        -> HostConfig.CpuShares
    blkio_weight (int) - Block IO (relative weight), between 10 and 1000
        -> HostConfig.BlkioWeight
    mem_limit (str) - Memory limit with units, such as 4m. The following
    are supported: b, k, m, g
        -> HostConfig.Memory
    """
    ret = {
        'CPU': _denormalize_value('cpu', config['CpuQuota']),
        'Mem': _denormalize_value('mem', config['Memory']),
        # 'IO': _denormalize_value('io', config['BlkioWeight']),
    }
    return ret

@bp.route('/update', methods=['GET'])
def update():
    """
    Update a container setting

    We take the following required args:
    c: (str) The container name

    """
    c = _normalize_name(request.args.get('c'))
    component = request.args.get('component')
    val = int(request.args.get('val'))
    config = {
        'container': c,
        'settings': {}
    }
    c = component.lower()
    if c == 'cpu':
        config['settings']['cpu_quota'] = _normalize_value(c, val)
    if c == 'io':
        config['settings']['blkio_weight'] = _normalize_value(c, val)
    if c == 'mem':
        config['settings']['mem_limit'] = str(_normalize_value(c, val)) + "m"
        config['settings']['memswap_limit'] = -1
    #print(config['settings'])
    c = client.containers.get(config['container'])
    c.update(**config['settings'])
    return {}

def _range():
    range_path = os.path.join(app.app.root_path, 'range.yml')
    with open(range_path, 'r') as fh_:
        slider_range = yaml.load(fh_, Loader=yaml.FullLoader)
    return slider_range

def _denormalize_value(code, val):
    """
    Take a current value and return the percentage val
    """
    slider_range = _range()
    lval, uval = slider_range[code]
    ret = ((val - min([uval, lval])) / (max([lval, uval]) - min([lval-uval]))) + 1
    return int(ret)
    # val_range = abs(uval - lval)
    # if lval < uval:
    #     return int(100 - ((val / val_range) * 100))
    # else:
    #     return int((val / val_range) * 100)


def _normalize_value(code, val):
    """
    This uses the range.yml configuration file which populates
    a set of values to determine the upper and lower range.
    We take our input value from the web interface to this function
    which is in the range of 0-100 and we turn that into an actual
    value to pass to the toxic
    """
    slider_range = _range()

    lval, uval = slider_range[code]

    # val_range = abs(uval - lval) + 1
    # # if lval < uval:
    # #     ret = abs(uval - int(val_range * (val / 100)))
    # # else:
    # #     # ret = int(val_range * (val / 100))
    # #     adder = range / val 
    # #     ret = uval + adder
    #print('received: ', val)
    #print('range vals', lval, uval)
    ret = (((val) * max([lval, uval]) - min([lval, uval])) / 100) + min([lval, uval])
    # range = abs(max[lval, uval] - min([lval, uval]))
    
    #print('attempt to set to: ', ret)
    return int(ret)
