# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, send_from_directory
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


from app.api.docker import bp as api_docker  # noqa E402
app.register_blueprint(api_docker, url_prefix='/api/docker')


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/scratch')
def scratch():
    return render_template("scratch.html")


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
