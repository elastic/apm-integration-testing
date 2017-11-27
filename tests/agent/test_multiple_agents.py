import requests
from timeout_decorator import TimeoutError
from tests.agent.concurrent_requests import Concurrent


def test_conc_req_flask_foobar(elasticsearch, apm_server, flask, django, express):
    flask_f = Concurrent.Endpoint(flask.foo.url,
                                  flask.app_name,
                                  ["__main__.foo"],
                                  "GET /foo",
                                  events_no=500)
    flask_b = Concurrent.Endpoint(flask.bar.url,
                                  flask.app_name,
                                  ["__main__.bar", "__main__.extra"],
                                  "GET /bar",
                                  events_no=500)
    django_f = Concurrent.Endpoint(django.foo.url,
                                   django.app_name,
                                   ["foo.views.foo"],
                                   "GET foo.views.show",
                                   events_no=500)
    django_b = Concurrent.Endpoint(django.bar.url,
                                   django.app_name,
                                   ["bar.views.bar", "bar.views.extra"],
                                   "GET bar.views.show",
                                   events_no=500)
    express_f = Concurrent.Endpoint(express.foo.url,
                                    express.app_name,
                                    [".*app.foo"],
                                    "GET /foo",
                                    events_no=500)
    express_b= Concurrent.Endpoint(express.bar.url,
                                   express.app_name,
                                   [".*app.bar", ".*app.extra"],
                                   "GET /bar",
                                   events_no=500)
    Concurrent(elasticsearch,
               [flask_f, flask_b, django_f, django_b, express_f, express_b],
               iters=1).run()
