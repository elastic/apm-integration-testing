# -*- coding: utf-8 -*-
from flask import Blueprint

bp = Blueprint('api', __name__)

from dyno.app.api import control  # noqa E402
