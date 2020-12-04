# -*- coding: utf-8 -*-
import docker
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
    return {
        'cpu': config['CpuShares'],
        'io': config['BlkioWeight'],
        'mem_limit': config['Memory']
        }


@bp.route('/update', methods=['GET'])
def update():
    """
    Update a container setting

    We take the following required args:
    c: (str) The container name

    """
    c = _normalize_name(request.args.get('c'))
    component = request.args.get('component')
    val = request.args.get('val')
    config = {
        'container': c,
        'settings': {}
    }
    if component.lower() == 'cpu':
        config['settings']['cpu_quota'] = int(val)
    if component.lower() == 'io':
        config['settings']['blkio_weight'] = int(val)
    if component.lower() == 'mem':
        config['settings']['mem_limit'] = str(val)

    c = client.containers.get(config['container'])
    c.update(**config['settings'])
    return {}
