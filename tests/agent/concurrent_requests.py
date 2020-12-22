from datetime import datetime, timedelta
import copy
import os
import logging
import time
from tornado import ioloop, httpclient

import timeout_decorator


FOO = "foo"
BAR = "bar"


def lookup(d, *keys):
    d1 = copy.deepcopy(d)
    for k in keys:
        d1 = d1[k]
    return d1


def anomaly(x):
    return x > 500000 or x < 0  # 0.5 secs


class Concurrent:
    class Endpoint:
        def __init__(self, url, app_name, span_names, transaction_name,
                     events_no=1000):
            self.url = url
            self.app_name = app_name
            self.span_names = span_names
            self.transaction_name = transaction_name
            self.events_no = events_no
            self.no_per_event = {
                "span": len(span_names),
                "transaction": 1
            }
            if app_name in ("flaskapp", "djangoapp"):
                self.agent = "python"
            elif app_name in ("expressapp",):
                self.agent = "nodejs"
            elif self.app_name in ("railsapp",):
                self.agent = "ruby"
            elif self.app_name in ("gonethttpapp",):
                self.agent = "go"
            elif self.app_name in ("springapp",):
                self.agent = "java"
            elif self.app_name in ("dotnetapp",):
                self.agent = "dotnet"
            else:
                raise Exception(
                    "Missing agent for app {}".format(app_name))

        def count(self, name):
            return self.no_per_event.get(name, 0) * self.events_no

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
        if r.code != 200:
            ioloop.IOLoop.instance().stop()
            message = "Bad response, aborting: {} - {} ({})".format(r.code, r.error, r.request_time)
            self.logger.error(message)
            raise Exception(message)

        self.num_reqs -= 1
        if self.num_reqs == 0:
            self.logger.debug("Stopping tornado I/O loop")
            ioloop.IOLoop.instance().stop()

    def load_test(self):
        http_client = httpclient.AsyncHTTPClient(max_clients=4)
        for endpoint in self.endpoints:
            for _ in range(endpoint.events_no):
                self.num_reqs += 1
                http_client.fetch(endpoint.url, self.handle, method='GET',
                                  connect_timeout=90, request_timeout=120)

        self.logger.debug("Starting tornado I/O loop")
        ioloop.IOLoop.instance().start()

    def check_counts(self, it, max_wait=60, backoff=1):
        err = "queried for {}, expected {}, got {}"

        def assert_count(terms, expected):
            """wait a bit for doc count to reach expectation"""

            @timeout_decorator.timeout(max_wait)
            def check_count(mut_actual):
                while True:
                    rsp = self.es.count(index=self.index, body=self.elasticsearch.term_q(terms))
                    mut_actual[0] = rsp["count"]
                    if mut_actual[0] >= expected:
                        return
                    time.sleep(backoff)

            mut_actual = [-1]  # keep actual count in this mutable
            try:
                check_count(mut_actual)
            except timeout_decorator.TimeoutError:
                pass
            actual = mut_actual[0]
            assert actual == expected, err.format(terms, expected, actual)

        self.es.indices.refresh()

        transactions_count = self.count("transaction") * it
        assert_count([{"processor.event": "transaction"}], transactions_count)

        spans_count = self.count("span") * it
        assert_count([{"processor.event": "span"}], spans_count)

        transactions_sum = spans_sum = 0
        for ep in self.endpoints:
            for span_name in ep.span_names:
                count = ep.count("span") * it / len(ep.span_names)
                spans_sum += count
                assert_count([
                    {"span.name": span_name},
                    {"context.service.name": ep.app_name}
                ], count)

            count = ep.count("transaction") * it
            transactions_sum += count
            assert_count([
                {'context.service.name': ep.app_name},
                {'transaction.name.keyword': ep.transaction_name}
            ], count)

        assert transactions_count == transactions_sum, err.format(
            "transactions all endpoints", transactions_count, transactions_sum)
        assert spans_count == spans_sum, err.format(
            "spans all endpoints", spans_count, spans_sum)

    def check_content(self, it, first_req, last_req, slack=None):
        # amount of slack time to give from request to capture within application
        slack = timedelta(seconds=2) if slack is None else slack
        for ep in self.endpoints:
            q = self.elasticsearch.term_q([
                {'context.service.name': ep.app_name},
                {'transaction.name.keyword': ep.transaction_name}
            ])
            rs = self.es.search(index=self.index, body=q)

            # ensure query for docs returns results
            tr_cnt = ep.count("transaction") * it
            total = lookup(rs, 'hits', 'total')
            if isinstance(total, int):
                actual_cnt = total
            else:
                actual_cnt = total["value"]
            assert tr_cnt == actual_cnt, "expected {} hits, got: {}".format(tr_cnt, actual_cnt)

            # check the first existing transaction for every endpoint
            hit = lookup(rs, 'hits', 'hits')[0]
            assert hit['_source']['processor'] == {'name': 'transaction', 'event': 'transaction'}

            transaction = lookup(hit, '_source', 'transaction')
            duration = lookup(transaction, 'duration', 'us')
            assert not anomaly(duration), (hit, duration)

            timestamp = datetime.strptime(lookup(hit, '_source', '@timestamp'), '%Y-%m-%dT%H:%M:%S.%fZ')
            assert first_req < timestamp < last_req + slack, \
                "transaction time {} outside of expected range {} - {}".format(timestamp, first_req, last_req)
            assert transaction['result'] == 'HTTP 2xx', transaction['result']

            context = lookup(hit, '_source', 'context')
            assert context['request']['method'] == "GET", context['request']['method']
            exp_p = os.path.basename(os.path.normpath(ep.url.split('?')[0]))
            p = context['request']['url']['pathname'].strip("/")
            assert p == exp_p, p

            tags = {}
            if 'tags' in context.keys():
                tags = context['tags']
            assert tags == {}, tags

            app_name = lookup(context, 'service', 'name')
            assert app_name == ep.app_name, app_name

            agent = lookup(context, 'service', 'agent', 'name')
            assert agent == ep.agent, agent
            assert transaction['type'] == 'request'

            try:
                framework = lookup(context, 'service', 'framework', 'name')
            except KeyError:
                # The Go agent doesn't support reporting framework:
                #   https://github.com/elastic/apm-agent-go/issues/69
                assert agent in ('go', 'java'), agent + ' agent did not report framework name'

            search = context['request']['url']['search']
            lang = lookup(context, 'service', 'language', 'name')
            if agent == 'nodejs':
                assert lang == "javascript", context
                assert framework in ("express",), context
                assert search == '?q=1', context
            elif agent == 'python':
                assert lang == "python", context
                assert framework in ("django", "flask",), context
                assert search == '?q=1', context
            elif agent == 'ruby':
                assert lang == "ruby", context
                assert framework in ("Ruby on Rails",), context
            elif agent == 'go':
                assert lang == "go", context
                assert transaction['type'] == 'request'
                assert search == 'q=1', context
            elif agent == 'java':
                assert lang == "Java", context
                assert transaction['type'] == 'request'
                assert search == 'q=1', context
            elif agent == 'dotnet':
                assert lang == "C#", context
                assert framework in ("ASP.NET Core",), context
                assert search == 'q=1', context
            else:
                raise Exception("Undefined agent {}".format(agent))

            span_q = self.elasticsearch.term_q([
                {'processor.event': 'span'},
                {'transaction.id': transaction['id']}
            ])
            rs = self.es.search(index=self.index, body=span_q)
            span_hits = lookup(rs, 'hits', 'hits')
            assert len(span_hits) == ep.no_per_event["span"]
            for span_hit in span_hits:
                assert span_hit['_source']['processor'] == {'event': 'span', 'name': 'transaction'}, span_hit

                span = lookup(span_hit, '_source', 'span')
                assert span["name"] in ep.span_names, span

                span_context = lookup(span_hit, '_source', 'context')
                span_app_name = lookup(span_context, 'service', 'name')
                assert span_app_name == ep.app_name, span_context

                if 'start' in span:
                    span_start = lookup(span, 'start', 'us')
                    assert not anomaly(span_start), span_start

                span_duration = lookup(span, 'duration', 'us')
                assert not anomaly(span_duration), (hit, span_duration)

                assert span_duration < duration * 10, \
                    "span duration {} is more than 10X bigger than transaction duration{}".format(
                        span_duration, duration)

                if 'stacktrace' in span.keys():
                    stacktrace = span['stacktrace']
                    assert 1 < len(stacktrace) < 70, \
                        "number of frames not expected, got {}, but this assertion might be too strict".format(
                            len(stacktrace))

                    fns = [frame['function'] for frame in stacktrace]
                    assert all(fns), fns
                    for attr in ['abs_path', 'line', 'filename']:
                        assert all(
                            frame.get(attr) for frame in stacktrace), stacktrace[0].keys()

    def run(self):
        self.logger.debug("Testing started..")
        self.elasticsearch.clean()

        start_load = datetime.utcnow()
        for it in range(1, self.iters + 1):
            self.logger.debug("Sending batch {} / {}".format(it, self.iters))
            self.load_test()
            self.check_counts(it)
            # wait until counts are solid
            end_load = datetime.utcnow()
            self.check_content(it, start_load, end_load)
            self.logger.debug("So far so good...")
        self.logger.debug("All done")
