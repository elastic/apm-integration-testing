# -*- coding: utf-8 -*-

import elasticapm
from flask import Flask
from elasticapm.contrib.flask import ElasticAPM

app = Flask(__name__)
app.debug = False

app.config['ELASTIC_APM'] = {
    'DEBUG': True,
    'TRACES_SEND_FREQ': 1,
    'SERVER': 'http://apm_server:8200',
}

apm = ElasticAPM(
    app,
    app_name='flask_app',
    secret_token=''
)


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
