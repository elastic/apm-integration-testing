from tests.agent.concurrent_requests import Concurrent


def test_conc_req_all_agents(es, apm_server, flask, django, dotnet, express, rails, go_nethttp, java_spring):
    dotnet_f = Concurrent.Endpoint(dotnet.foo.url,
                                   dotnet.app_name,
                                   ["foo"],
                                   "GET /foo",
                                   events_no=500)
    dotnet_b = Concurrent.Endpoint(dotnet.bar.url,
                                   dotnet.app_name,
                                   ["bar", "extra"],
                                   "GET /bar",
                                   events_no=500)
    flask_f = Concurrent.Endpoint(flask.foo.url,
                                  flask.app_name,
                                  ["app.foo"],
                                  "GET /foo",
                                  events_no=500)
    flask_b = Concurrent.Endpoint(flask.bar.url,
                                  flask.app_name,
                                  ["app.bar", "app.extra"],
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
                                    ["app.foo"],
                                    "GET /foo",
                                    events_no=500)
    express_b = Concurrent.Endpoint(express.bar.url,
                                    express.app_name,
                                    ["app.bar", "app.extra"],
                                    "GET /bar",
                                    events_no=500)
    rails_f = Concurrent.Endpoint(rails.foo.url,
                                  rails.app_name,
                                  ["ApplicationController#foo"],
                                  "ApplicationController#foo",
                                  events_no=500)
    rails_b = Concurrent.Endpoint(rails.bar.url,
                                  rails.app_name,
                                  ["ApplicationController#bar", "app.extra"],
                                  "ApplicationController#bar",
                                  events_no=500)
    go_nethttp_f = Concurrent.Endpoint(go_nethttp.foo.url,
                                       go_nethttp.app_name,
                                       ["foo"],
                                       "GET /foo",
                                       events_no=500)
    go_nethttp_b = Concurrent.Endpoint(go_nethttp.bar.url,
                                       go_nethttp.app_name,
                                       ["bar", "extra"],
                                       "GET /bar",
                                       events_no=500)
    java_spring_f = Concurrent.Endpoint(java_spring.foo.url,
                                        java_spring.app_name,
                                        ["foo"],
                                        "GreetingController#foo",
                                        events_no=500)
    java_spring_b = Concurrent.Endpoint(java_spring.bar.url,
                                        java_spring.app_name,
                                        ["bar", "extra"],
                                        "GreetingController#bar",
                                        events_no=500)

    Concurrent(es, [
        dotnet_f, dotnet_b,
        flask_f, flask_b,
        django_f, django_b,
        express_f, express_b,
        rails_b, rails_f,
        go_nethttp_f, go_nethttp_b,
        java_spring_f, java_spring_b,
    ], iters=1).run()
