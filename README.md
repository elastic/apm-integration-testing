# APM Integration Testing

This repo contains tools for end to end (eg agent -> apm server -> elasticsearch <- kibana) development and testing of Elastic APM.

[![Build Status](https://apm-ci.elastic.co/buildStatus/icon?job=apm-integration-tests%2Fmaster)](https://apm-ci.elastic.co/job/apm-integration-tests/job/master/)

## Prerequisites

The basic requirements for starting a local environment are:

- Docker
- Docker compose
- Python (version 3 preferred)

This repo is tested with Python 3 but best effort is made to make starting/stopping environments work with Python 2.7.

### Docker

[Installation instructions](https://www.docker.com/community-edition)

### Docker compose
[Installation instructions](https://docs.docker.com/compose/install/)

### Python 3

- Windows: [Installation instructions](https://www.python.org/downloads/windows/)
- Mac (using [Homebrew](https://brew.sh/)):
  ```sh
  brew install python
  ```
- Debian/Ubuntu
  ```sh
  sudo apt-get install python3
  ```

## Running Local Enviroments

### Starting an Environment

`./scripts/compose.py` provides a handy cli for starting a testing environment using docker-compose.
`make venv` creates a virtual environment with all of the python-based dependencies needed to run `./scripts/compose.py` - it requires `virtualenv` in your `PATH`.
Activate the virtualenv with `source venv/bin/activate` and use `./scripts/compose.py --help` for information on subcommands and arguments. Finally, you can execute the following command to list all available parameter to start the environment `./scripts/compose.py start --help`.

[APM LocalEnv Quickstart](QUICKSTART.md)

#### Logging in

By default, Security is enabled, which means you need to log into Kibana and/or authenticate with Elasticsearch.
An assortment of users is provided to test different scenarios:

 * `admin`
 * `apm_server_user`
 * `apm_user_ro`
 * `kibana_system_user`
 * `*_beat_user`
 
The password for all default users is `changeme`.

### Stopping an Environment

All services:
```
./scripts/compose.py stop

# OR

docker-compose down
```

All services and clean up volumes and networks:
```
make stop-env
```

Individual services:
```
docker-compose stop <service name>
```

## Example environments

We have a list with the most common flags combination that we internally use when developing our APM solution. You can find the list here:

|Persona | Flags | Motivation / Use Case | Team | Comments |
|--------|-------|-----------------------|------|----------|
| CI Server | `python scripts/compose.py start 8.0.0 --java-agent-version ${COMMIT_SHA} --build-parallel --with-agent-java-spring --no-apm-server-dashboards --no-apm-server-self-instrument --no-kibana --force-build` | Prepare environment for running tests for APM Java agent | APM Agents |
| CI Server	| `python scripts/compose.py start 8.0.0 --apm-server-build https://github.com/elastic/apm-server@${COMMIT_HASH} --build-parallel --no-apm-server-dashboards --no-apm-server-self-instrument --with-agent-rumjs --with-agent-dotnet --with-agent-go-net-http --with-agent-nodejs-express --with-agent-ruby-rails --with-agent-java-spring --with-agent-python-django --with-agent-python-flask --force-build`	| Prepare environment for running tests for APM Server	| APM Server | |
| Demos & Screenshots	| `./scripts/compose.py start --release --with-opbeans-dotnet --with-opbeans-go --with-opbeans-java --opbeans-java-agent-branch=pr/588/head --force-build --with-opbeans-node --with-opbeans-python --with-opbeans-ruby --with-opbeans-rum --with-filebeat --with-metricbeat 7.3.0`	| demos, screenshots, ad hoc QA. It's also used to send heartbeat data to the cluster for Uptime | PMM	| Used for snapshots when close to a release, without the `--release` flag |
| Development | `./scripts/compose.py start 7.3 --bc --with-opbeans-python --opbeans-python-agent-local-repo=~/elastic/apm-agent-python` | Use current state of local agent repo with opbeans | APM Agents | This works perfectly for Python, but has problems with Node.js. We are not mounting the local folder as a volume, but copy it. This is to avoid any side effects to the local repo. The node local dev folder can get very large due to node_modules, which takes some time to copy. |
| | `./scripts/compose.py start 7.3 --bc --start-opbeans-deps` | This flag would start all opbeans dependencies (postgres, redis, apm-server, ...), but not any opbeans instances | APM Agents | This would help when developing with a locally running opbeans. Currently, we start the environment with a `--with-opbeans-python` flag, then stop the opbeans-python container manually |
| Developer | `./scripts/compose.py start master --no-apm-server` | Only use Kibana + ES in desired version for testing | APM Server |  |
| Developer | `./scripts/compose.py start --release 7.3 --no-apm-server` | Use released Kibana + ES, with custom agent and server running on host, for developing new features that span agent and server. | APM Agents | If `--opbeans-go-agent-local-repo` worked, we might be inclined to use that instead of running custom apps on the host. Would have been handy while developing support for breakdown graphs. Even then, it's probably still faster to iterate on the agent without involving Docker. |
| Demos & Compettive | `./scripts/compose.py start 6.7.0 --release --with-services ~/src/elastic/apm-dev/docs/static/jaeger.json --with-services ~/src/elastic/apm-dev/docs/static/zipkin.json --with-services ~/src/elastic/apm-dev/docs/static/haystack.json` | Integration / comparison with external products that we'd prefer not to include in compose.py | APM | https://github.com/elastic/apm-dev/blob/master/docs/competitive.md |
| Developer | `./scripts/compose.py start master --no-kibana` | Use newest ES/master, with custom kibana on host, for developing new features in kibana | APM |  |
| Developer | `./scripts/compose.py start 6.3 --with-kafka --with-zookeeper --apm-server-output=kafka --with-logstash --with-agent-python-flask` | Testing with kafka and logstash ingestion methods | APM |  |	
| Developer | `./scripts/compose.py start master --no-kibana --with-opbeans-node --with-opbeans-rum --with-opbeans-x` | Developing UI features locally | APM UI | |
| Developer | `./scripts/compose.py start master --docker-compose-path - --skip-download --no-kibana --with-opbeans-ruby --opbeans-ruby-agent-branch=master > docker-compose.yml` | Developing UI features againt specific configuration | APM UI | We sometimes explicity write a `docker-compose.yml` file and tinker with it until we get the desired configuration becore running `docker-compose up` |
| Developer | `scripts/compose.py start ${version}` | Manual testing of agent features | APM Agents | |
| Developer | `./scripts/compose.py start master --with-opbeans-java --opbeans-java-agent-branch=pr/588/head --apm-server-build https://github.com/elastic/apm-server.git@master` | Test with in-progress agent/server features | APM UI |  |
| Developer | `compose.py start 7.0 --release --apm-server-version=6.8.0` | Upgrade/mixed version testing | APM | Then, without losing es data, upgrade/downgrade various components |


### Change default ports

Expose Kibana on http://localhost:1234:

    ./scripts/compose.py start master --kibana-port 1234

### Opbeans

Opbeans are demo web applications that are instrumented with Elastic APM.
Start `opbeans-*` services and their dependencies along with apm-server, elasticsearch, and kibana:

    ./scripts/compose.py start --all master


This will also start the `opbeans-load-generator` service which, by default,
will generate random requests to all started backend Opbeans services.
To disable load generation for a specific service, use the `--no-opbeans-XYZ-loadgen` flag.

Opbeans RUM does not need a load generation service,
as it is itself generating load using a headless chrome instance.

#### Start Opbeans with a specific agent branch

You can start Opbeans with an agent which is built from source from a specific branch or PR.
This is currently only supported with the go and the Java agent.

Example which builds the https://github.com/elastic/apm-agent-java/pull/588 branch from source and uses an APM server built from master:

    ./scripts/compose.py start master --with-opbeans-java --opbeans-java-agent-branch=pr/588/head --apm-server-build https://github.com/elastic/apm-server.git@master

Note that it may take a while to build the agent from source.

Another example, which installs the [APM Python
Agent](https://github.com/elastic/apm-agent-python) from the `master` branch
for testing against [opbeans-python](https://github.com/elastic/opbeans-python)
(for example, for end to end log correlation testing):

    ./scripts/compose.py start master --with-opbeans-python --with-filebeat --opbeans-python-agent-branch=master --force-build

Note that we use `--opbeans-python-agent-branch` to define the python agent
branch for opbeans-python, rather than `--python-agent-package`, which only
applies to the `--with-python-agent-*` flags for the small integration test
apps.


### Uploading Sourcemaps

The frontend app packaged with opbeans-node runs in a production build, which means the source code is minified. The APM server needs the corresponding sourcemap to unminify the code.

You can upload the sourcemap with this command:

    ./scripts/compose.py upload-sourcemap

In the standard setup, it will find the config options itself, but they can be overwritten. See

    ./scripts/compose.py upload-sourcemap --help

### Kafka output

    ./scripts/compose.py start --with-kafka --with-zookeeper --apm-server-output=kafka --with-logstash master

Logstash will be configured to ingest events from kafka.

Topics are named according to service name. To view events for 1234_service-12a3:

    docker exec -it localtesting_6.3.0-SNAPSHOT_kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic apm-1234_service-12a3 --from-beginning --max-messages 100

Onboarding events will go to the apm topic.

Note that index templates are not loaded automatically when using outputs other than Elasticsearch.  Create them manually with:

    ./scripts/compose.py load-dashboards

If data was inserted before this point (eg an opbeans service was started) you'll probably have to delete the auto-created `apm-*` indexes and let them be recreated.

## Advanced topics

### Dumping docker-compose.yml

`./scripts/compose.py start master --docker-compose-path - --skip-download` will dump the generated `docker-compose.yml` to standard out (`-`) without starting any containers or downloading images.

Omit `--skip-download` to just download images.

### Testing compose

`compose.py` includes unittests, `make test-compose` to run.

## Running Tests

Additional dependencies are required for running the integration tests:
- python3
- virtualenv

On a Mac with Homebrew:

```sh
brew install pyenv-virtualenv
```

All integration tests are written in python and live under `tests/`.

Several `make` targets exist to make their execution simpler:

- test-server
- test-kibana
- test-agent-{go,node,python,ruby,...}

These targets will create a python virtual environment in `venv` with all of the dependencies need to run the suite.

Each target requires a running test environment, providing an apm-server, elasticsearch, and others depending on the particular suite.

Tests should always eventually be run within a docker container to ensure a consistent, repeatable environment for reporting.

Prefix any of the `test-` targets with `docker-` to run them in a container eg: `make docker-test-server`.

### Network issues diagnose

It is possible to diagnose Network issues related with lost documents
between APM Agent, APM server, or Elasticsearch,
in order to do that, you have to add the `--with-packetbeat` argument
to your command line.
When you add this argument an additional Docker container running Packetbeat is
attached to the APM Server Docker container,
this container will grab information about the communication between APM Agent,
APM server, and Elasticsearch that you can analyze in case of failure.
When a test fails, data related to Packetbeat and APM is dumped
with [elasticdump](https://www.npmjs.com/package/elasticdump) into a couple
of files `/app/tests/results/data-NAME_OF_THE_TEST.json`
and `/app/tests/results/packetbeat-NAME_OF_THE_TEST.json`

### Continuous Integration

Jenkins runs the scripts from `.ci/scripts` and is viewable at https://apm-ci.elastic.co/.

Those scripts shut down any existing testing containers and start a fresh new environment before running tests unless the `REUSE_CONTAINERS` environment variable is set.

These are the scripts available to execute:

* `all.sh:` runs all test on apm-server and every agent type.
* `common.sh:` common scripts variables and functions, it does not execute anything.
* `dotnet.sh:` runs .NET tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `go.sh:` runs Go tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `java.sh:` runs Java tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `kibana.sh:` runs kibana agent tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `nodejs.sh:` runs Nodejs agent tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `opbeans.sh:` runs the unit tests for the apm-integration-testing app and validate the linting, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `python.sh:` runs Python agent tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `ruby.sh:` runs Ruby agent tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `server.sh:` runs APM Server tests, you can choose the versions to run see the [environment variables](#environment-variables) configuration.
* `unit-tests.sh:` runs the unit tests for the apm-integration-testing app and validate the linting, you can choose the versions to run see the [environment variables](#environment-variables) configuration.

#### Environment Variables

It is possible to configure some options and versions to run by defining environment variables before to launch the scripts

* `COMPOSE_ARGS`: replaces completely the default arguments compose.py used by scripts, see the compose.py help to know which ones you can use.
* `DISABLE_BUILD_PARALLEL`: by default Docker images are built in parallel, if you set `DISABLE_BUILD_PARALLEL=true` the Docker images will build in serie. It helps to make the logs more readable.
* `BUILD_OPTS`: aggregates arguments to default arguments passing to compose.py see the compose.py help to know which ones you can use.
* `ELASTIC_STACK_VERSION`: selects the Elastic Stack version to use on tests, by default is is used the master branch. You can choose any branch or tag from the Github repo.
* `APM_SERVER_BRANCH`: selects the APM Server version to use on tests, by default it uses the master branch. You can choose any branch or tag from the Github repo.
* `APM_AGENT_DOTNET_VERSION`: selects the agent .NET version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)
* `APM_AGENT_GO_VERSION`: selects the agent Go version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)
* `APM_AGENT_JAVA_VERSION`: selects the agent Java version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)
* `APM_AGENT_NODEJS_VERSION`: selects the agent Nodejs version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)
* `APM_AGENT_PYTHON_VERSION`: selects the agent Python version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)
* `APM_AGENT_RUBY_VERSION`: selects the agent Ruby version to use, by default it uses the master branch. See [specify an agent version](#specify-an-agent-version)

#### Specify an Agent Version

You can choose any release, branch, or tag from the Github repo, to do that you have to set the PKG environment variable to `MODE;VERSION`, where `MODE` can be:

* `github`: to get VERSION from branches and tags.
* `release`: to get VERSION from releases.
* `commit`: to get VERSION from commits (only Java and Go agents).

e.g.
* `APM_AGENT_NODEJS_VERSION=github;v1.0.0` It will try to get v1.0.0 branch or tag from Github.
* `APM_AGENT_NODEJS_VERSION=github;master` It will try to get master branch or tag from Github.
* `APM_AGENT_NODEJS_VERSION=release;v1.0.0` It will try to get v1.0.0 from releases repo.
* `APM_AGENT_RUBY_VERSION=release;latest` It will try to get latest from releases repo.
* `APM_AGENT_JAVA_VERSION=commit;539f1725483804d32beb4f780eac72c238329cb1` It will try to get `539f1725483804d32beb4f780eac72c238329cb1` from repo commits.

#### Version tests

Various combinations of versions of agents and the Elastic Stack are tested together to ensure compatibility.
The matrix is defined using [apm_server.yml](https://github.com/elastic/apm-integration-testing/blob/master/tests/versions/apm_server.yml) for one axis and then a per-agent specification for the other axis.
Certain exclusions are defined on a per agent basis.
For example, [the nodejs matrix](https://apm-ci.elastic.co/view/All/job/elastic+apm-integration-testing+master+multijob-nodejs-agent-versions/) is defined in [nodejs.yml](https://github.com/elastic/apm-integration-testing/blob/master/tests/versions/nodejs.yml).
When those tests run, `scripts/ci/versions_nodejs.sh` is invoked with the product of those files, eg `scripts/ci/versions_nodejs.sh 'github;master' '6.3'`.
The Elastic Stack version argument accepts an optional list of semi-colon separated arguments that will be passed to `scripts/compose.py` when building the test stack.

### Agent Development

To run integration tests against unreleased agent code, start an environment where that agent code is used by the test application.

For example, to test an update to the python agent from user `elasticcontributor` on their `newfeature1` branch:

```bash
# start test deps: apm-server, elasticsearch, and the two python test applications
# the test applications will use elasticcontributor's newfeature1 apm agent
./scripts/compose.py start master --no-kibana --with-agent-python-django --with-agent-python-flask --python-agent-package=git+https://github.com/elasticcontributor/apm-agent-python.git@newfeature1 --force-build

# wait for healthiness
docker-compose ps

# run tests
make test-agent-python
```

Testing unrelease code for other agents follows a simliar pattern.

See `version*` in https://github.com/elastic/apm-integration-testing/tree/master/.ci/scripts for details on how CI tests specific agent/elastic stack version combinations.

### Testing docker images

Tests are written using [bats](https://github.com/sstephenson/bats) under the docker/tests dir

    make -C docker test-<app>
    make -C docker test-opbeans-<agent>
    make -C docker test-<agent>

Test all the docker images for the Opbeans

    make -C docker all-opbeans-tests

Test all the docker images for the agents

    make -C docker all-agents-tests
