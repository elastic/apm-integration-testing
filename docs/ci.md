# APM Ingtegration Tests CI

## Introduction

The APM Integration tests run regularly on [apm-ci.elastic.co](https://apm-ci.elastic.co/job/apm-integration-tests). They test the interaction between the various APM agents and the APM server to ensure that functionality is working as-expected.

## Identifiying failures

If a failure in the APM Integration tests occur in the CI, an investigation should be conducted to ensure that it does not represent a regression.

If a job shows a failure, log output may be produced from the test suite which shows the error. Below is an example of a failed test in the Node.js agent:

```
Error Message

AssertionError: queried for [('processor.event', 'transaction'), ('service.name', ['expressapp', 'expressapp'])], expected 1820, got 1002

Stacktrace

es = <tests.fixtures.es.es.<locals>.Elasticsearch object at 0x7f121a692550>
apm_server = <tests.fixtures.apm_server.apm_server.<locals>.APMServer object at 0x7f121a692fd0>
express = <tests.fixtures.agents.Agent object at 0x7f11e43abb10>

    def test_conc_req_node_foobar(es, apm_server, express):
        foo = Concurrent.Endpoint(express.foo.url,
                                  express.app_name,
                                  ["app.foo"],
                                  "GET /foo")
        bar = Concurrent.Endpoint(express.bar.url,
                                  express.app_name,
                                  ["app.bar", "app.extra"],
                                  "GET /bar",
                                  events_no=820)
>       Concurrent(es, [foo, bar], iters=1).run()

tests/agent/test_nodejs.py:37: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
tests/agent/concurrent_requests.py:298: in run
    self.check_counts(it)
tests/agent/concurrent_requests.py:136: in check_counts
    assert_count([("processor.event", "transaction"), ("service.name", service_names)], transactions_count)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

terms = [('processor.event', 'transaction'), ('service.name', ['expressapp', 'expressapp'])]
expected = 1820

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
>       assert actual == expected, err.format(terms, expected, actual)
E       AssertionError: queried for [('processor.event', 'transaction'), ('service.name', ['expressapp', 'expressapp'])], expected 1820, got 1002

tests/agent/concurrent_requests.py:130: AssertionError
```

## Understanding downstream jobs

The main APM Integration job is an orchestrator which launches a set of downstream jobs which execute independently in Jenkins. The results are then collected by the upstream job and displayed to the user.

Therefore, in order to effectively troubleshoot a failure in the primary job, it is necessary to identify which downstream job(s) failed and then to navigate to the downstream job to conduct an investigation.

To determine the correct downstream job, several approaches are available:

### Method 1: Using the console log to find the downstream job

To use this method, first determine which downstream job failed by examining the name of the job failure. In the above example of a Node.JS failure, the name of the failing test is shown in the CI as `Integration Tests / All / tests.agent.test_nodejs.test_conc_req_express`.

The name of the downstream job is the second field in the name, in this case that is  `All`.

To navigate to the downstream job for `All`, open the Console Log and look for the section like the following:

```
[UI] 03:09:52  Scheduling project: APM Integration Test Downstream » master
[Java]03:10:03  Starting building: APM Integration Test Downstream » master #6241
[All] 03:10:03  Starting building: APM Integration Test Downstream » master #6238
[Ruby] 03:10:03  Starting building: APM Integration Test Downstream » master #6244
[Node.js] 03:10:03  Starting building: APM Integration Test Downstream » master #6242
[.NET] 03:10:03  Starting building: APM Integration Test Downstream » master #6239
[Go] 03:10:03  Starting building: APM Integration Test Downstream » master #6240
[Rum] 03:10:03  Starting building: APM Integration Test Downstream » master #6245
[UI] 03:10:03  Starting building: APM Integration Test Downstream » master #6246
[Python] 03:10:03  Starting building: APM Integration Test Downstream » master #6243
```

⚠️ Ensure that you are looking at the section of the log which contains links to individual builds, as indicated by a specific build number, such as `#6242` in the list above for the Node.js job.

Click on the link for the job corresponding to the failure you wish to investigate. For our example case, this would be `[Node.js] 03:10:03  Starting building: APM Integration Test Downstream » master #6242` as we have already determined that this is a `Node.js` failure.

### Method 2: Using Blue Ocean to find the downstream job

From the failed APM Integration test build, click on the link in the sidebar for `Open Blue Ocean`.

From there, navigate to the failed test(s) as indicated by a red circle with an X through the center.

Click the drop-down for the `Build` step.

⚠️ Note that this is not the drop-down for the failed step! Instead, it is the step for the build itself, which is usually indicated by a very long runtime (tens of minutes) as compared to the other steps which typically complete in seconds. It is typically the first step in the list.

When clicking on the drop-down, output such as the following will be displayed:

```
[2020-08-17T03:09:52.686Z] Scheduling project: APM Integration Test Downstream » master

[2020-08-17T03:10:03.310Z] Starting building: APM Integration Test Downstream » master #6238
```

As you can see, the build number of the downstream job is listed there. To navigate to the build in question, go to the [Downstream Jobs](https://apm-ci.elastic.co/job/apm-integration-test-downstream/) view in Jenkins. Then choose the same branch as the failure you are investigating and then view the list of builds in the pane on the left-hand side of the screen. Search for the build with the same number as above. In our example, this is build `#6238`.
