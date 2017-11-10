# APM Integration Testing 

__WIP__

## Installation
Use the python environment of your choice and run:
```
pip install -r requirements.txt
```

## Running Testsuite
```
pytest
```

### TODOs:
- make all URLs configurable via ENV_VARIABLES
- improve docker setup
  - install requirements at runtime
  - use ENTRYPOPINT over CMD
  - ensure volumes are removed
  - check docker user permissions
- fix bug in concurrent requests when different number of events given for two endpoints.
- add concurrent tests for nodejs


## Development Info
- Tests should be runnable also on cloud. 
  The setup should be seperated from the test logic.
  Right now fixtures are used for defining setup per testcase.
  When running tests on cloud dependencies will be started ahead and probably passed in by a URL.
- Writing agent code: Reuse as much logic as possible to also point out differences in agents.
- Possible structure of tests:
  - smoke tests (very high level, runnable on different platforms, could be used for unified build)
  - version tests (high level tests between agents-server-es-kibana) to be run with different snapshots or release candidates
  - extensive end-to-end-tests (test different config, types of requests, etc.)
