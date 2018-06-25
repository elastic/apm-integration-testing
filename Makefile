SHELL := /bin/bash
PYTHON ?= python
PYTHON3 ?= python3
VENV ?= ./venv

COMPOSE_ARGS ?=

JUNIT_RESULTS_DIR=tests/results
JUNIT_OPT=--junitxml $(JUNIT_RESULTS_DIR)

# Make sure we run local versions of everything, particularly commands
# installed into our virtualenv with pip eg. `docker-compose`.
export PATH := ./bin:$(VENV)/bin:$(PATH)

all: test

# The tests are written in Python. Make a virtualenv to handle the dependencies.
# make doesn't play nicely with custom VENV, intended only for CI usage
venv: requirements.txt
	test -d $(VENV) || virtualenv --python=$(PYTHON3) $(VENV);\
	pip install -r requirements.txt;\
	touch $(VENV);\

lint: venv
	flake8 tests/ scripts/compose.py

.PHONY: lint

start-env: venv
	$(PYTHON) scripts/compose.py start $(COMPOSE_ARGS)
	docker-compose up -d

stop-env: venv
	docker-compose down -v --remove-orphans || true

destroy-env: venv
	(docker ps -aqf network=apm-integration-testing | xargs docker rm -f && docker network rm apm-integration-testing) || true

# default (all) started for now
env-%: venv
	$(MAKE) start-env

test: test-all

test-agent-%-version: venv
	pytest tests/agent/test_$*.py -v -m version $(JUNIT_OPT)/agent-$*-version-junit.xml

test-agent-%: venv
	pytest tests/agent/test_$*.py -v $(JUNIT_OPT)/agent-$*-junit.xml

test-compose: venv
	pytest scripts/compose.py -v $(JUNIT_OPT)/compose-junit.xml

test-compose-2:
	virtualenv --python=python2.7 venv2
	./venv2/bin/pip2 install mock pytest pyyaml
	./venv2/bin/pytest --noconftest scripts/compose.py

test-kibana: venv
	pytest tests/kibana/test_integration.py -v $(JUNIT_OPT)/kibana-junit.xml

test-server: venv
	pytest tests/server/ -v $(JUNIT_OPT)/server-junit.xml

test-all: venv test-compose lint
	pytest -v $(JUNIT_OPT)/all-junit.xml

docker-test-%:
	TARGET=test-$* $(MAKE) dockerized-test

dockerized-test:
	@echo waiting for services to be healthy
	docker-compose-wait

	@echo running make $(TARGET) inside a container
	docker build --pull -t apm-integration-testing .

	mkdir -p -m 777 "$(PWD)/$(JUNIT_RESULTS_DIR)"
	chmod 777 "$(PWD)/$(JUNIT_RESULTS_DIR)"
	docker run \
	  --name=apm-integration-testing \
	  --network=apm-integration-testing \
	  --security-opt seccomp=unconfined \
	  -e APM_SERVER_URL=http://apm-server:8200 \
	  -e ES_URL=http://elasticsearch:9200 \
	  -e KIBANA_URL=http://kibana:5601 \
	  -e DJANGO_URL="http://djangoapp:8003" \
	  -e EXPRESS_URL="http://expressapp:8010" \
	  -e FLASK_URL="http://flaskapp:8001" \
	  -e GO_NETHTTP_URL="http://gonethttpapp:8080" \
	  -e RAILS_URL="http://railsapp:8020" \
	  -e PYTHONDONTWRITEBYTECODE=1 \
	  -v "$(PWD)/$(JUNIT_RESULTS_DIR)":"/app/$(JUNIT_RESULTS_DIR)" \
	  --rm \
	  --entrypoint make \
	  apm-integration-testing \
	  $(TARGET)

.PHONY: test-% docker-test-% dockerized-test
