SHELL := /bin/bash
PYTHON ?= python
PYTHON3 ?= python3

COMPOSE_ARGS ?=

# Make sure we run local versions of everything, particularly commands
# installed into our virtualenv with pip eg. `docker-compose`.
export PATH := ./bin:./venv/bin:$(PATH)

all: test

# The tests are written in Python. Make a virtualenv to handle the dependencies.
venv: requirements.txt
	test -d venv || virtualenv --python=$(PYTHON3) venv;\
	venv/bin/python venv/bin/pip install -r requirements.txt;\
	touch venv;\

lint: venv
	flake8 tests/
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

test: test-all lint

test-agent-%-version: venv
	pytest tests/agent/test_$*.py -v -m version

test-agent-%: venv
	pytest tests/agent/test_$*.py -v

test-compose: venv
	$(PYTHON) -munittest scripts.compose -v

test-kibana: venv
	pytest tests/kibana/test_integration.py -v

test-server: venv
	pytest tests/server/ -v

test-all: venv test-compose
	pytest -v --ignore=tests/agent/test_ruby.py

docker-test-%:
	TARGET=test-$* $(MAKE) dockerized-test

dockerized-test:
	@echo waiting for services to be healthy
	docker-compose-wait

	@echo running make $(TARGET) inside a container
	docker build --pull -t apm-integration-testing .

	docker run \
	  --name=apm-integraion-testing \
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
	  --rm \
	  --entrypoint make \
	  apm-integration-testing \
	  $(TARGET)

.PHONY: test-% docker-test-% dockerized-test
