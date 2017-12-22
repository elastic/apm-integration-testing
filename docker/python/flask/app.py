# -*- coding: utf-8 -*-

import elasticapm
from flask import Flask
from elasticapm.contrib.flask import ElasticAPM
from elasticapm.handlers.logging import LoggingHandler
import logging
import os

app = Flask(__name__)
app.debug = False

app.config['ELASTIC_APM'] = {
    'DEBUG': True,
    'TRANSACTION_SEND_FREQ': 1,
    'MAX_EVENT_QUEUE_LENGTH': 1,
    'SERVER_URL': os.environ['APM_SERVER_URL'],
    'SERVICE_NAME': os.environ['FLASK_SERVICE_NAME'],
    'SECRET_TOKEN': '1234',
    'TRANSACTIONS_IGNORE_PATTERNS': ['.*healthcheck']
}
apm = ElasticAPM(app, logging=True)


@app.route('/')
def index():
    return 'OK'


@app.route('/healthcheck')
def healthcheck():
    return 'OK'


@app.route('/foo')
def foo_route():
    return foo()


@elasticapm.capture_span()
def foo():
    return "foo"


@app.route('/bar')
def bar_route():
    return bar()


@elasticapm.capture_span()
def bar():
    extra()
    return "bar"


@elasticapm.capture_span()
def extra():
    return "extra"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ['FLASK_PORT'])

    # Create a logging handler and attach it.
    handler = LoggingHandler(client=apm.client)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
