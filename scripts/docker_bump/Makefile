.PHONY: help

JUNIT_RESULTS_DIR=tests/results
JUNIT_OPT=--junitxml $(JUNIT_RESULTS_DIR)
PYTHON ?= python3
export PYTHONPATH=../..

help: ## Display this help text
	@grep -E '^[a-zA-Z_-]+[%]?:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'


build-requirements:  ## Build the requirements file. Necessary after any addition to pyproject.toml, such as after the invocation of `poetry add <mod>`
	poetry export --dev -f requirements.txt --output requirements.txt

run:  ## Run the bumper to generate a list of outdated images
	$(PYTHON) -m scripts.docker_bump.bumper;
