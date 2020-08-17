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
    'DEBUG': os.environ.get('ELASTIC_APM_LOG_LEVEL').lower() == 'debug',
    'SERVER_URL': os.environ['APM_SERVER_URL'],
    'SERVICE_NAME': os.environ['FLASK_SERVICE_NAME'],
    'TRANSACTION_SEND_FREQ': 1,  # 1.x
    'FLUSH_INTERVAL': 1,  # 2.x
    'MAX_EVENT_QUEUE_LENGTH': 1,  # 1.x
    'MAX_QUEUE_SIZE': 1,  # 2.x
    'API_REQUEST_TIME': '50ms',  # 4.x
    'SECRET_TOKEN': os.getenv('APM_SERVER_SECRET_TOKEN', '1234'),
    'TRANSACTIONS_IGNORE_PATTERNS': ['.*healthcheck']
}
apm = ElasticAPM(app, logging=logging.ERROR)


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


@app.route('/oof')
def oof_route():
    raise Exception('oof')


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s %(asctime)s %(process)d %(message)s', level=logging.WARNING)
    logging.getLogger('elasticapm').setLevel(os.environ.get("ELASTIC_APM_LOG_LEVEL", "ERROR").upper())
    app.run(host='0.0.0.0', port=int(os.environ['FLASK_PORT']))

