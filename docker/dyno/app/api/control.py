# -*- coding: utf-8 -*-
from flask import request
from app.api import bp


@bp.route('/apps', methods=['GET'])
def fetch_all_apps():
    """
    Generate a list of the apps we have configured
    and return it
    """
    pass
