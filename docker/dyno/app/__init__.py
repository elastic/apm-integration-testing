# -*- coding: utf-8 -*-
from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

from app.cfg import Config as Cfg


def create_app(config_class=Cfg):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)
    return app


app = create_app()
# TODO additional configure and move to redis for cache and limiter
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["500 per hour"]
)

from app.api import bp as api_bp  # noqa E402
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/')
def index():
    return render_template("index.html")
