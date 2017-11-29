SHELL := /bin/bash

dockerized_tests:
	python ./scripts/start_services.py

tests:
	python ./scripts/wait_until_services_running.py ${URLS}
	${TEST_CMD}

.PHONY: dockerized_tests tests
