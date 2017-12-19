# APM Integration Testing 

__WIP__

## Installation Requirements
- docker
This repo is tested with python 3. 

## Running Testsuite
Start any script from `scripts/ci`.

Tests should always be run within a docker container, as services are connected via a shared network. 
The setup of the services needed is done by the script `scripts/start_services.py`, which is triggered from all test scripts within `scripts/ci`.

### TODOs:
- add tests
- improve docker setup
  - use ENTRYPOPINT over CMD
  - check docker user permissions

## Development Info
- Add a pre-commit hook for autopep8 formatting:
    - wget https://raw.githubusercontent.com/chibiegg/git-autopep8/master/pre-commit -O .git/hooks/pre-commit
    - chmod +x .git/hooks/pre-commit
- Tests should be runnable also on cloud. 
  The setup should be separated from the test logic.
  When running tests on cloud dependencies will be started ahead and probably passed in by a URL.
- Writing agent code: Reuse as much logic as possible to also point out differences in agents.
- Possible structure of tests:
  - smoke tests (very high level, runnable on different platforms, could be used for unified build)
  - version tests (high level tests between agents-server-es-kibana) to be run with different snapshots or release candidates
  - extensive end-to-end-tests (test different config, types of requests, etc.)
