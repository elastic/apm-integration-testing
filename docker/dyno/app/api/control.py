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
import yaml
from dyno import app
from flask import request
from dyno.app.api import bp
from toxiproxy.server import Toxiproxy

"""
The `toxic_map` is a dictionary which maps
shortened "codes" into dictionaies which contain
fields for the type and attribute of the toxic

For more information on Toxics and how they work,
please see:

https://github.com/Shopify/toxiproxy#toxics
"""
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


def _fetch_proxy():
    """
    Return a connection to the Toxiproxy instance which
    is an interface to the Python toxiproxy library. For
    more information on the library and its use, pleas see:

    https://github.com/douglas/toxiproxy-python

    Note
    ----
    To use this function, you *must* have the following
    environment variables defined: `TOXI_HOST`, `TOXI_PORT`,
    which represent the hostname and port respectively of the
    Toxiproxy server you wish to control.  If these are not
    defined then this function will return None.

    Note
    ----
    The proxy instance which is returned is *not* a singleton
    and multiple calls will result in multiple proxy instances.

    Returns
    -------
    Instance of toxiproxy.server.Toxiproxy() if environment variables
    are set, otherwise None is returned.
    """
    proxy_server = Toxiproxy()
    if 'TOXI_HOST' in os.environ and 'TOXI_PORT' in os.environ:
        proxy_server.update_api_consumer(os.environ['TOXI_HOST'], os.environ['TOXI_PORT'])
    return proxy_server


@bp.route('/app', methods=['GET'])
def fetch_app():
    """
    Fetch the configured toxics for single Opbeans app

    Note
    ----
    Exposed via HTTP at /api/control/app
    Supported HTTP methods: GET

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    name : str
        The application to fetch

    denorm : bool
        Whether or not values should be denormalized. Typically used for
        interaction with graphical slider UIs.

    Returns
    -------
    dict
        Dictionary containing information about the proxy for the application

    Examples
    --------
	❯ curl -s "http://localhost:9000/api/app?name=opbeans-python"|jq
	{
	  "enabled": true,
	  "listen": "[::]:8000",
	  "name": "opbeans-python",
	  "toxics": {},
	  "upstream": "opbeans-python:3000"
	}
    """
    name = request.args.get('name')
    denorm = request.args.get('denorm')
    toxiproxy = _fetch_proxy()
    proxies = toxiproxy.proxies()
    proxy = proxies.get(name)
    ret = {}
    if not proxy:
        return {}
    ret['name'] = proxy.name
    ret['listen'] = proxy.listen
    ret['upstream'] = proxy.upstream
    ret['enabled'] = proxy.enabled
    ret['toxics'] = {}

    for toxic in proxy.toxics().values():
        for attribute, value in toxic.attributes.items():
            if denorm:
                denorm_val = _encode_toxic(toxic.type, attribute)
                ret['toxics'][denorm_val] = _denormalize_value(denorm_val, value)
            else:
                ret['toxics'][attribute] = value
    return ret


@bp.route('/apps', methods=['GET'])
def fetch_all_apps():
    """
    Generate a list of the apps we have configured
    and return it

    Note
    ----
    Exposed via HTTP at /api/control/apps
    Supported HTTP methods: GET

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    full : str
        Pass full=1 to include configuration information for
        each proxy that is found

    Returns
    -------
    dict
        A dictionary containing all proxies. If `full` argument
        is provided, then each proxy in the list will contain
        its configuration information

    Examples
    --------
	❯ curl -s "http://localhost:9000/api/apps"|jq
	{
	  "proxies": [
	    "opbeans-python",
	    "postgres",
	    "redis"
	  ]
	}

	❯ curl -s "http://localhost:9000/api/apps?full=1"|jq
	{
	  "proxies": [
	    {
	      "listen": "[::]:8000",
	      "name": "opbeans-python"
	    },
	    {
	      "listen": "[::]:5432",
	      "name": "postgres"
	    },
	    {
	      "listen": "[::]:6379",
	      "name": "redis"
	    }
	  ]
	}
    """
    toxiproxy = _fetch_proxy()
    proxies = toxiproxy.proxies()
    if request.args.get('full'):
        ret = {'proxies': []}
        for proxy in proxies.values():
            name = proxy.name
            listen = proxy.listen
            ret['proxies'].append({'name': name, 'listen': listen})
        return ret
    # TODO We may need to update the server addr here
    return {'proxies': list(proxies.keys())}

@bp.route('/enable', methods=['GET'])
def enable_proxy():
    """
    Enable a proxy

    Note
    ----
    Exposed via HTTP at /api/control/apps
    Supported HTTP methods: GET

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    str : proxy
        The proxy to enable

    Returns
    -------
    dict
        An empty dict on success

    Examples
    --------
	❯ curl -s "http://localhost:9000/api/enable?proxy=opbeans-python"|jq
	{}
    """
    requested_proxy = request.args.get('proxy')

    toxiproxy = _fetch_proxy()
    toxiproxy.get_proxy(requested_proxy).enable()

    return {}

@bp.route('/disable', methods=['GET'])
def disable_proxy():
    """
    Disable a proxy

    Note
    ----
    Exposed via HTTP at /api/control/apps
    Supported HTTP methods: GET

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    str : proxy
        The proxy server to disable

    Returns
    -------
    dict
        An empty dict on success

    Example
    -------
    curl "http://localhost:9000/api/disable?proxy=opbeans-python"|jq
    {}

    """
    proxy = request.args.get('proxy')
    toxiproxy = _fetch_proxy()
    toxiproxy.get_proxy(proxy).disable()
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

    Note
    ----
    Exposed via HTTP at /api/control/apps
    Supported HTTP methods: GET

    Note
    ----
    Paramaters are received query arguments in a Flask request object. They
    may not be passed directly to this function.

    Parameters
    ----------
    str : tox_code
        The toxic to change. See the map at the top of this file for a list of
        possible values.

    str : proxy
        The proxy to modify

    int : val
        The value to set

    Returns
    -------
    dict
        Empty dictionary on success

    Examples
    --------
    > curl -s --header "Content-Type: application/json" \
    --request POST \
    --data '{"tox_code":"L","proxy":"opbeans-python","val":100}' \
    http://localhost:9000/api/slide
    {}
    """
    # TODO fully document tox codes
    slide = request.get_json() or {}
    toxic_key = _decode_toxic(slide['tox_code'])

    t = _fetch_proxy()
    p = t.get_proxy(slide.get('proxy'))
    normalized_val = _normalize_value(slide['tox_code'], slide['val'])

    # See if toxic exists
    if not p.get_toxic('{}_downstream'.format(toxic_key['type'])):
        p.add_toxic(
            type=toxic_key['type'],
            attributes={toxic_key['attr']: normalized_val}
            )
    else:
        """
        Note: This functionality is not in the upstream library and
        has been added specifically here:
        https://github.com/cachedout/toxiproxy-python/
        """
        p.edit_toxic(
           type=toxic_key['type'],
           attributes={toxic_key['attr']: normalized_val}
        )
    return {}


def _range():
    """
    Helper function to deserialize the contents of the range.yml file

    Returns
    -------
    dict
        The contents of range.yml
    """
    range_path = os.path.join(app.app.root_path, 'range.yml')
    with open(range_path, 'r') as fh_:
        slider_range = yaml.load(fh_, Loader=yaml.FullLoader)
    return slider_range

# TODO possibly swap names?
def _denormalize_value(tox_code, val):
    """
    Given a raw value from a toxic, which should exist
    inside the range as specified by the range.yaml configuration
    file, this function returns a "denormalized" value between
    1-100, which can then in turn be used by sliders in the UI.

    Parameters
    ----------
    str : tox_code
        A toxic code, which corresponds to one of the keys in the dictionary
        at the top of this file.

    int : val
        A raw value to set

    Returns
    -------
    int
        A value between 1-100 which corresponds to how much the input
        deviates from the mean.
    """
    slider_range = _range()
    lval, uval = slider_range[tox_code]
    val_range = abs(uval - lval) + 1
    if lval < uval:
        return int(100 - ((val / val_range) * 100))
    else:
        return int((val / val_range) * 100)


def _normalize_value(tox_code, val):
    """
    This uses the range.yml configuration file which populates
    a set of values to determine the upper and lower range.
    We take our input value from the web interface to this function
    which is in the range of 0-100 and we turn that into an actual
    value to pass to the toxic

    Parameters
    ----------
    str : tox_code
        A toxic code, which corresponds to one of the keys in the dictionary
        at the top of this file.

    int : val
        A value between 1-100

    Returns
    -------
    int
        A raw value between the range of numbers specified in the range.yml file
    """
    slider_range = _range()
    lval, uval = slider_range[tox_code]
    val_range = abs(uval - lval) + 1
    if lval < uval:
        ret = abs(uval - int(val_range * (val / 100)))
        if ret < 1:
            ret = 1
        return ret

    ret = int(val_range * (val / 100))
    if ret < 1:
        ret = 1
    return ret

def _encode_toxic(toxic_type, attribute):
    """
    Given a type and an attr, return the tox code

    Parameters
    ----------
    str : toxic_type
        A type of toxic. See the dict at the top of this file
        for examples of toxic types

    str : attribute
        A toxic attribute. See the dict at the top of this file
        for examples of toxic attributes

    Returns
    -------
    str
        The tox code
    """
    for key, val in toxic_map.items():
        if val['type'] == toxic_type and val['attr'] == attribute:
            return key
    return None


def _decode_toxic(toxic):
    """

    """
    try:
        return toxic_map[toxic]
    except KeyError:
        return {}
