# APM Integration Testing 

__WIP__

## Installation Requirements
- docker
This repo is tested with python 3. 

## Integration testing

### Starting an Environment

`scripts/compose.py` provides a handy cli for starting a testing environment using docker-compose.
Use `scripts/compose.py --help` for information on subcommands and arguments.

#### Example environments

- `start --all-opbeans` - start `opbeans-*` services and their dependencies along with apm-server, elasticsearch, and kibana
- `start --with-kafka --with-zookeeper --output=kafka --with-logstash` - configure apm-server to emit events via kafka and logstash to ingest them

#### Advanced topics

- `start --docker-compose-path -` will dump the generated `docker-compose.yml` to standard out without starting any containers.
- `compose.py` includes unittests, `make test-compose` to run.

### Running Tests

All integration tests are written in python and live under `tests/`.

Several `make` targets exist to make their execution simpler:

- test-server
- test-kibana
- test-agent-{go,node,python,ruby,...}

These targets will create a python virtual environment in `venv` with all of the dependencies need to run the suite.

Each target requires a running test environment, providing an apm-server, elasticsearch, and others depending on the particular suite.

Tests should always eventually be run within a docker container to ensure a consistent, repeatable environment for
reporting.
Prefix any of the `test-` targets with `docker-` to run them in a container eg: `make docker-test-server`.

#### Continuous Integration

CI runs the scripts from `scripts/ci/`.

Those scripts shut down any existing testing containers and start a fresh new environment before running tests.

## Development Info
- Add a pre-commit hook for autopep8 formatting:
    - curl -Lo .git/hooks/pre-commit https://raw.githubusercontent.com/chibiegg/git-autopep8/master/pre-commit
    - chmod +x .git/hooks/pre-commit
- Tests should be runnable also on cloud. 
  The setup should be separated from the test logic.
  When running tests on cloud dependencies will be started ahead and probably passed in by a URL.
- Writing agent code: Reuse as much logic as possible to also point out differences in agents.
- Possible structure of tests:
  - smoke tests (very high level, runnable on different platforms, could be used for unified build)
  - version tests (high level tests between agents-server-es-kibana) to be run with different snapshots or release candidates
  - extensive end-to-end-tests (test different config, types of requests, etc.)
