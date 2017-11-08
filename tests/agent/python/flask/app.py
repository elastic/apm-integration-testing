# -*- coding: utf-8 -*-

import elasticapm
from flask import Flask
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler
import logging

app = Flask(__name__)
app.debug = False

app.config['ELASTIC_APM'] = {
    'DEBUG': True,
    'TRACES_SEND_FREQ': 1,
    'SERVER': 'http://apm_server:8200',
    'APP_NAME': 'flask_app',
    'SECRET_TOKEN': '1234'
}
apm = ElasticAPM(app, logging=True)


@app.route('/')
def index():
    return 'OK'


@app.route('/foo')
def foo_route():
    return foo()


@elasticapm.trace()
def foo():
    return "foo"


@app.route('/bar')
def bar_route():
    return bar()


@elasticapm.trace()
def bar():
    return "OK"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8001)

    # Create a logging handler and attach it.
    handler = LoggingHandler(client=apm.client)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
