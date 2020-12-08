# -*- coding: utf-8 -*-
import os
import app
import docker
import yaml
from flask import request

from flask import Blueprint

bp = Blueprint('docker', __name__)


client = docker.from_env()
low_client = docker.APIClient()


def _normalize_name(name):
    """
    Small helper to find the container name. We get
    passed in something like `elasticsearch` and have to
    find it in a list of container names that are like:
    localtesting_7.9.0_elasticsearch
    """
    containers = container_list()
    for c in containers['containers']:
        if c.split('_').pop().strip() == name:
            return c


@bp.route('/list', methods=['GET'])
def container_list():
    """
    Return list of containers
    """
    ret = {'containers': []}
    containers = client.containers.list()
    for c in containers:
        ret['containers'].append(c.name)
    return ret


@bp.route('/query', methods=['GET'])
def query():
    """
    Inspect container and return information

    Args:

    c: (str) Container to get
    """
    c = request.args.get('c')
    config = low_client.inspect_container(_normalize_name(c))['HostConfig']
    # We take the following:
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
    import pprint
    pprint.pprint(config)
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
        config['settings']['memswap_limit'] = _normalize_value(c, val)

    c = client.containers.get(config['container'])
    c.update(**config['settings'])
    return {}


def _denormalize_value(code, val):
    """
    Take a current value and return the percentage val
    """
    range_path = os.path.join(app.app.root_path, 'range.yml')
    with open(range_path, 'r') as fh_:
        slider_range = yaml.load(fh_)
    lval, uval = slider_range[code]
    val_range = abs(uval - lval)
    if lval < uval:
        return int(100 - ((val / val_range) * 100))
    else:
        return int((val / val_range) * 100)

def _normalize_value(code, val):
    """
    This uses the range.yml configuration file which populates
    a set of values to determine the upper and lower range.
    We take our input value from the web interface to this function
    which is in the range of 0-100 and we turn that into an actual
    value to pass to the toxic
    """
    range_path = os.path.join(app.app.root_path, 'range.yml')
    with open(range_path, 'r') as fh_:
        slider_range = yaml.load(fh_)

    lval, uval = slider_range[code]
    val_range = abs(uval - lval)
    if lval < uval:
        ret = abs(uval - int(val_range * (val / 100)))
    else:
        ret = int(val_range * (val / 100))

    # if code == 'mem':
    #     ret = str(ret) + "B"
    return ret
