# -*- coding: utf-8 -*-
from flask import request
from app.api import bp
from toxiproxy.server import Toxiproxy


@bp.route('/apps', methods=['GET'])
def fetch_all_apps():
    """
    Generate a list of the apps we have configured
    and return it
    """
    t = Toxiproxy()
    p = t.proxies()    
    # TODO We may need to update the server addr here
    return {'proxies': list(p.keys())}


@bp.route('/enable', methods=['GET'])
def enable_proxy():
    proxy = request.args.get('proxy')
    print(proxy)
    # FIXME testing
    t = Toxiproxy()
    p = t.get_proxy(proxy)
    p.enable()
    return {}

@bp.route('/disable', methods=['GET'])
def disable_proxy():
    proxy = request.args.get('proxy')
    print(proxy)
    # FIXME testing
    t = Toxiproxy()
    p = t.get_proxy(proxy)
    p.disable()
    return {}


@bp.route('/slide', methods=['POST'])
def slide():
    """
    This function receives adjustments from the sliders
    and adjusts thresholds accordingly. If toxics are not
    present, this method will create them.

    It should receive a JSON document similar to the following:
    {'proxy': 'postgres, 'tox_code': 'L', 'val: 10}

    In this scheme, `tox_code` is just shorthand for a particular
    toxic as described here: https://github.com/shopify/toxiproxy#toxics
    """
    # TODO fully document tox codes
    slide = request.get_json() or {}
    toxic_key = _decode_toxic(slide['tox_code'])
    # FIXME testing
    t = Toxiproxy()
    p = t.get_proxy(slide.get('proxy'))
    # TODO right now there isn't any edit functionality in the upstream lib
    # so we need to add that and send in a PR. For now, we check and see if
    # a toxic matching what we are looking for exists and if so, we remove it.
    # Then we just carry on with our business. This obviously needs to be fixed
    # at some point.

    # FIXME testing. Let's just add for now for PoC
    try:
        p.add_toxic(
            type=toxic_key['type'],
            attributes={toxic_key['attr']: slide['val']}
            )
    except Exception:
        t = p.toxics()
        for i in t:
            p.destroy_toxic(i)
        p.add_toxic(
            type=toxic_key['type'],
            attributes={toxic_key['attr']: slide['val']}
            )
    return {}


def _decode_toxic(toxic):
    toxic_map = {
        'L': {'type': 'latency', 'attr': 'latency'},
        'J': {'type': 'latency', 'attr': 'jitter'},
        'B': {'type': 'bandwidth', 'attr': 'rate'},
        'SC': {'type': 'slow_close', 'attr': 'delay'},
        'T': {'type': 'timeout', 'attr': 'timeout'},
        'Sas': {'type': 'slicer', 'attr': 'average_size'},
        'Ssv': {'type': 'slicer', 'attr': 'size_variation'},
        'Sd': {'type': 'slicer', 'attr': 'delay'},
        'Ld': {'type': 'limit_data', 'attr': 'bytes'}
    }
    try:
        return toxic_map[toxic]
    except KeyError:
        return {}
