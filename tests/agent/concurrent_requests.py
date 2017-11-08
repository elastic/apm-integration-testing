import time
from tornado import ioloop, httpclient
from datetime import datetime, timedelta
import logging
import copy
import os
import pdb


FOO = "foo"
BAR = "bar"


def lookup(d, *keys):
    d1 = copy.deepcopy(d)
    for k in keys:
        d1 = d1[k]
    return d1


def anomaly(x):
    return x > 100000 or x < 1  # 100000 = 0.1 sec


class Concurrent:

    class Endpoint:

        def __init__(self, url, app_name, trace_names, transaction_name,
                     events_no=1000):
            self.url = url
            self.app_name = app_name
            self.trace_names = trace_names
            self.transaction_name = transaction_name
            self.events_no = events_no
            self.no_per_event = {
                "trace": len(trace_names),
                "transaction": 1
            }
            self.set_agent

        def count(self, name):
            return self.no_per_event.get(name, 0) * self.events_no

        def set_agent(self):
            if self.app_name in ("flask_app", "django_app"):
                self.agent = "elasticapm-python"
            elif self.app_name in ("express_app"):
                self.agent = "nodejs"
            else:
                raise Exception("Missing agent for app {}".format(self.app_name))


    def __init__(self, elasticsearch, endpoints, iters=1, index="apm-*"):
        self.num_reqs = 0
        self.index = index
        # TODO: improve ES handling
        self.elasticsearch = elasticsearch
        self.es = elasticsearch.es
        self.endpoints = endpoints
        self.iters = iters
        self.set_logger()

    def count(self, name):
        return sum(ep.count(name) for ep in self.endpoints)

    def set_logger(self):
        logger = logging.getLogger("logger")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(process)s] [%(levelname)s] [%(funcName)s - \
            %(lineno)d]  %(message)s')
        handler.setFormatter(formatter)
        logger.propagate = False
        logger.addHandler(handler)
        self.logger = logger

    def handle(self, r):
        try:
            assert r.code == 200
            self.num_reqs -= 1
            if self.num_reqs == 0:
                self.logger.info("Stopping tornado I/O loop")
                ioloop.IOLoop.instance().stop()

        except AssertionError:
            self.num_reqs == 0
            ioloop.IOLoop.instance().stop()
            self.logger.error(
                "Bad response, aborting: {} - {} ({})".format(
                    r.code, r.error, r.request_time))

    def load_test(self):
        http_client = httpclient.AsyncHTTPClient(max_clients=4)
        for endpoint in self.endpoints:
            for _ in range(endpoint.events_no):
                self.num_reqs += 1
                http_client.fetch(endpoint.url, self.handle, method='GET',
                                  connect_timeout=90, request_timeout=120)

        self.logger.info("Starting tornado I/O loop")
        ioloop.IOLoop.instance().start()

    def check_counts(self, it):
        err = "queried for {}, expected {}, got {}"
        def assert_count(field, value, count):
            rs = self.es.count(index=self.index,
                               body=self.elasticsearch.regexp_q(field, value))
            assert rs['count'] == count, err.format(value, count, rs)

        self.es.indices.refresh()

        transactions_count = self.count("transaction") * it
        assert_count("processor.event", "transaction", transactions_count)

        traces_count = self.count("trace") * it
        assert_count("processor.event", "trace", traces_count)

        transactions_sum = traces_sum = 0
        for ep in self.endpoints:
            for trace_name in ep.trace_names:
                count = ep.count("trace") * it / len(ep.trace_names)
                traces_sum += count
                assert_count("trace.name", trace_name, count)

            count = ep.count("transaction") * it
            transactions_sum += count
            assert_count("transaction.name.keyword", ep.transaction_name, count)

        assert transactions_count == transactions_sum, err.format("transactions all endpoints", transactions_count, transactions_sum)
        assert traces_count == traces_sum, err.format("traces all endpoints", traces_count, traces_sum)

    def check_content(self, it):
        for ep in self.endpoints:
            q = self.elasticsearch.regexp_q("transaction.name", ep.transaction_name)
            rs = self.es.search(index=self.index, body=q)
            for hit in lookup(rs, 'hits', 'hits'):

                assert hit['_source']['processor'] == {'name': 'transaction',
                                                       'event': 'transaction'}

                transaction = lookup(hit, '_source', 'transaction')

                duration = lookup(transaction, 'duration', 'us')
                assert not anomaly(duration), duration

                timestamp = datetime.strptime(lookup(hit, '_source', '@timestamp'),
                                              '%Y-%m-%dT%H:%M:%S.%fZ')
                assert datetime.utcnow() - timedelta(minutes=it) < timestamp < datetime.utcnow(), \
                    "{} is too far of {} ".format(timestamp, datetime.utcnow())

                assert transaction['result'] == '200', transaction['result']
                assert transaction['type'] == 'request'

                context = lookup(hit, '_source', 'context')
                assert context['request']['method'] == "GET", context['request']['method']
                assert context['request']['url']['hostname'] == 'localhost'
                pathname = os.path.basename(os.path.normpath(ep.url))
                assert context['request']['url']['pathname'] == pathname, \
                    context['request']['url']['pathname']

                assert context['tags'] == {}, context

                app_name = lookup(context, 'app', 'name')
                assert app_name == ep.app_name, app_name

                agent = lookup(context, 'app', 'agent', 'name')
                assert agent == ep.agent, agent

                search = context['request']['url']['search']
                framework = lookup(context, 'app', 'framework', 'name')
                if agent == 'nodejs':
                    assert context['response']['status_code'] == 200, context['response']['status_code']
                    assert context['user'] == {}, context
                    assert context['custom'] == {}, context
                    assert search == '?', context
                    lang = lookup(context, 'app', 'runtime', 'name')
                    assert lang == "node", context
                    assert framework in ("express"), context
                elif agent == 'elasticapm-python':
                    assert search == '', context
                    lang = lookup(context, 'app', 'language', 'name')
                    assert lang == "python", context
                    assert framework in ("django", "flask"), context
                else:
                    raise Exception("Undefined agent {}".format(agent))


                traces_query = self.elasticsearch.term_q("processor.event", "trace")
                traces_query = {'query': { 'bool': { 'must': [
                    { 'term': {
                        'processor.event': 'trace'
                    }},
                    { 'term': {
                        'trace.transaction_id': transaction['id']
                    }}
                ]}}}
                trace_hits = lookup(self.es.search(self.index, body=traces_query), 'hits', 'hits')
                assert len(trace_hits) == ep.no_per_event["trace"]
                for trace_hit in trace_hits:
                    assert trace_hit['_source']['processor'] == {'name': 'trace',
                                                                 'event': 'transaction'}

                    trace = lookup(trace_hit, '_source', 'trace')
                    assert trace["name"] == ep.trace_name

                    trace_context = lookup(trace_hit, '_source', 'context')
                    trace_app_name = lookup(trace_context, 'app', 'name')
                    assert trace_app_name == ep.app_name

                    trace_start = lookup(trace, 'start', 'us')
                    assert not anomaly(trace_start), trace_start

                    trace_duration = lookup(trace, 'duration', 'us')
                    assert not anomaly(trace_duration), trace_duration

                    assert trace_duration < duration * 10, \
                        "trace duration {} is more than 10X bigger than transaction duration{}".format(
                            trace_duration, duration)

                    stacktrace = trace['stacktrace']
                    assert 15 < len(stacktrace) < 30, \
                        "number of frames not expected, got {}, but this assertion might be too strict".format(
                            len(stacktrace))

                    fns = [frame['function'] for frame in stacktrace]
                    assert all(fns), fns
                    for attr in ['abs_path', 'line', 'filename']:
                        assert all(
                            frame.get(attr) for frame in stacktrace), stacktrace[0].keys()

    def run(self):
        self.logger.info("Testing started..")
        self.elasticsearch.clean()

        for it in range(1, self.iters + 1):
            self.logger.info("Sending batch {} / {}".format(it, self.iters))
            self.load_test()
            time.sleep(3)
            self.check_counts(it)
            self.check_content(it)
            self.logger.info("So far so good...")
        self.logger.info("ALL DONE")
