.PHONY: help
SHELL := /bin/bash
PYTHON ?= python3
VENV ?= ./venv

COMPOSE_ARGS ?=

JUNIT_RESULTS_DIR=tests/results
JUNIT_OPT=--junitxml $(JUNIT_RESULTS_DIR)

CERT_VALID_DAYS ?= 3650

APM_SERVER_URL ?= http://apm-server:8200
ES_URL ?= http://elasticsearch:9200
KIBANA_URL ?= http://kibana:5601
DJANGO_URL ?= http://djangoapp:8003
DOTNET_URL ?= http://dotnetapp:8100
EXPRESS_URL ?= http://expressapp:8010
FLASK_URL ?= http://flaskapp:8001
GO_NETHTTP_URL ?= http://gonethttpapp:8080
JAVA_SPRING_URL ?= http://javaspring:8090
PHP_APACHE_URL ?= http://phpapacheapp
RAILS_URL ?= http://railsapp:8020
RUM_URL ?= http://rum:8000

ES_USER ?= elastic
ES_PASS ?= changeme
ELASTIC_APM_SECRET_TOKEN ?= SuPeRsEcReT

PYTHONHTTPSVERIFY ?= 1

PYTEST_ARGS ?=

# Make sure we run local versions of everything, particularly commands
# installed into our virtualenv with pip eg. `docker-compose`.
export PATH := ./bin:$(VENV)/bin:$(PATH)

export APM_SERVER_URL := $(APM_SERVER_URL)
export KIBANA_URL := $(KIBANA_URL)
export ES_URL := $(ES_URL)
export ES_USER := $(ES_USER)
export ES_PASS := $(ES_PASS)
export ELASTIC_APM_SECRET_TOKEN := $(ELASTIC_APM_SECRET_TOKEN)
export PYTHONHTTPSVERIFY := $(PYTHONHTTPSVERIFY)

help: ## Display this help text
	@grep -E '^[a-zA-Z_-]+[%]?:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

all: test

# The tests are written in Python. Make a virtualenv to handle the dependencies.
# make doesn't play nicely with custom VENV, intended only for CI usage
venv: requirements.txt ## Prepare the virtual environment
	test -d $(VENV) || virtualenv -q --python=$(PYTHON) $(VENV);\
	source $(VENV)/bin/activate || exit 1;\
	pip install -q -r requirements.txt;\
	touch $(VENV);

lint: venv  ## Lint the project
	source $(VENV)/bin/activate; \
	flake8 --ignore=D100,D101,D102,D103,D104,D105,D106,D107,D200,D205,D400,D401,D403,W504  tests/ scripts/compose.py scripts/modules

.PHONY: create-x509-cert
create-x509-cert:  ## Create an x509 certificate for use with the test suite
	openssl req -x509 -newkey rsa:4096 -keyout scripts/tls/key.pem -out scripts/tls/cert.crt -days "${CERT_VALID_DAYS}" -subj '/CN=apm-server' -nodes

.PHONY: lint

build-env: venv ## Build the test environment
	source $(VENV)/bin/activate; \
	$(PYTHON) scripts/compose.py build $(COMPOSE_ARGS)
	docker-compose build --parallel

start-env: venv ## Start the test environment
	source $(VENV)/bin/activate; \
	$(PYTHON) scripts/compose.py start $(COMPOSE_ARGS)
	docker-compose up -d

stop-env: venv ## Stop the test environment
	source $(VENV)/bin/activate; \
	docker-compose down -v --remove-orphans || true

destroy-env: venv ## Destroy the test environment
	[ -n "$$(docker ps -aqf network=apm-integration-testing)" ] && (docker ps -aqf network=apm-integration-testing | xargs -t docker rm -f && docker network rm apm-integration-testing) || true

# default (all) built for now
build-env-%: venv
	$(MAKE) build-env

# default (all) started for now
env-%: venv
	$(MAKE) start-env

test: test-all  ## Run all the tests

test-agent-%-version: venv
	source $(VENV)/bin/activate; \
	pytest $(PYTEST_ARGS) tests/agent/test_$*.py --reruns 3 --reruns-delay 5 -v -s -m version $(JUNIT_OPT)/agent-$*-version-junit.xml

test-agent-%: venv ## Test a specific agent. ex: make test-agent-java
	source $(VENV)/bin/activate; \
	pytest $(PYTEST_ARGS) tests/agent/test_$*.py --reruns 3 --reruns-delay 5 -v -s $(JUNIT_OPT)/agent-$*-junit.xml

test-compose: venv
	source $(VENV)/bin/activate; \
	pytest $(PYTEST_ARGS) scripts/tests/*_tests.py --reruns 3 --reruns-delay 5 -v -s $(JUNIT_OPT)/compose-junit.xml

test-compose-2:
	virtualenv --python=python2.7 venv2
	./venv2/bin/pip2 install mock pytest pyyaml
	./venv2/bin/pytest $(PYTEST_ARGS) --noconftest scripts/tests/*_tests.py

test-kibana: venv ## Run the Kibana integration tests
	source $(VENV)/bin/activate; \
	pytest $(PYTEST_ARGS) tests/kibana/test_integration.py --reruns 3 --reruns-delay 5 -v -s $(JUNIT_OPT)/kibana-junit.xml

test-server: venv  ## Run server tests
	source $(VENV)/bin/activate; \
	pytest $(PYTEST_ARGS) tests/server/ --reruns 3 --reruns-delay 5 -v -s $(JUNIT_OPT)/server-junit.xml

SUBCOMMANDS = list-options load-dashboards start status stop upload-sourcemap versions

test-helps:
	$(foreach subcommand,$(SUBCOMMANDS), $(PYTHON) scripts/compose.py $(subcommand) --help > /tmp/file-output && echo "Passed $(subcommand)" || { echo "Failed $(subcommand). See output: " ; cat /tmp/file-output ; exit 1; };)

test-all: venv test-compose lint test-helps ## Run all the tests
	source $(VENV)/bin/activate; \
	pytest -v -s $(PYTEST_ARGS) $(JUNIT_OPT)/all-junit.xml

docker-test-%: ## Run a specific dockerized test. Ex: make docker-test-java
	TARGET=test-$* $(MAKE) dockerized-test

dockerized-test: ## Run all the dockerized tests
	./scripts/docker-summary.sh

	@echo running make $(TARGET) inside a container
	docker build --pull -t apm-integration-testing .

	mkdir -p -m 777 "$(PWD)/$(JUNIT_RESULTS_DIR)"
	chmod 777 "$(PWD)/$(JUNIT_RESULTS_DIR)"
	docker run \
		--name=apm-integration-testing \
		--network=apm-integration-testing \
		--security-opt seccomp=unconfined \
		-e APM_SERVER_URL=$${APM_SERVER_URL} \
		-e ES_URL=$${ES_URL} \
		-e KIBANA_URL=$${KIBANA_URL} \
		-e DJANGO_URL=$(DJANGO_URL) \
		-e DOTNET_URL=$(DOTNET_URL) \
		-e EXPRESS_URL=$(EXPRESS_URL) \
		-e FLASK_URL=$(FLASK_URL) \
		-e GO_NETHTTP_URL=$(GO_NETHTTP_URL) \
		-e JAVA_SPRING_URL=$(JAVA_SPRING_URL) \
		-e RAILS_URL=$(RAILS_URL) \
		-e RUM_URL=$(RUM_URL) \
		-e PHP_APACHE_URL=$(PHP_APACHE_URL) \
		-e PYTHONDONTWRITEBYTECODE=1 \
		-e PYTHONHTTPSVERIFY=$(PYTHONHTTPSVERIFY) \
		-e ENABLE_ES_DUMP=$(ENABLE_ES_DUMP) \
		-e ES_USER=$${ES_USER} \
		-e ES_PASS=$${ES_PASS} \
		-e ELASTIC_APM_SECRET_TOKEN=$${ELASTIC_APM_SECRET_TOKEN} \
		-v "$(PWD)/$(JUNIT_RESULTS_DIR)":"/app/$(JUNIT_RESULTS_DIR)" \
		--rm \
		--entrypoint make \
		apm-integration-testing \
		$(TARGET)

.PHONY: test-% docker-test-% dockerized-test docker-compose-wait
