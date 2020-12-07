# -*- coding: utf-8 -*-
import os
import app
import yaml
from flask import request
from app.api import bp
from toxiproxy.server import Toxiproxy


def _fetch_proxy():
    t = Toxiproxy()
    if 'TOXI_HOST' in os.environ and 'TOXI_PORT' in os.environ:
        t.update_api_consumer(os.environ['TOXI_HOST'], os.environ['TOXI_PORT'])
    return t


@bp.route('/apps', methods=['GET'])
def fetch_all_apps():
    """
    Generate a list of the apps we have configured
    and return it

    Can also pass full=1 for a more complete listing
    """
    t = _fetch_proxy()
    p = t.proxies()
    if request.args.get('full'):
        ret = {'proxies': []}
        for proxy in p.values():
            name = proxy.name
            listen = proxy.listen
            ret['proxies'].append({'name': name, 'listen': listen})
        return ret
    else:
        # TODO We may need to update the server addr here
        return {'proxies': list(p.keys())}


@bp.route('/enable', methods=['GET'])
def enable_proxy():
    proxy = request.args.get('proxy')
    print(proxy)
    # FIXME testing
    t = _fetch_proxy()
    p = t.get_proxy(proxy)
    p.enable()
    return {}

@bp.route('/disable', methods=['GET'])
def disable_proxy():
    proxy = request.args.get('proxy')
    print(proxy)
    # FIXME testing
    t = _fetch_proxy()
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
    t = _fetch_proxy()
    p = t.get_proxy(slide.get('proxy'))
    # TODO right now there isn't any edit functionality in the upstream lib
    # so we need to add that and send in a PR. For now, we check and see if
    # a toxic matching what we are looking for exists and if so, we remove it.
    # Then we just carry on with our business. This obviously needs to be fixed
    # at some point.
    normalized_val = _normalize_value(slide['tox_code'], slide['val'])

    # FIXME testing. Let's just add for now for PoC
    try:
        p.add_toxic(
            type=toxic_key['type'],
            attributes={toxic_key['attr']: normalized_val}
            )
    except Exception:
        t = p.toxics()
        for i in t:
            p.destroy_toxic(i)
        p.add_toxic(
            type=toxic_key['type'],
            attributes={toxic_key['attr']: normalized_val}
            )
    return {}


def _normalize_value(tox_code, val):
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

    lval, uval = slider_range[tox_code]
    val_range = abs(uval - lval)
    if lval < uval:
        return abs(uval - int(val_range * (val / 100)))
    else:
        return int(val_range * (val / 100))


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
