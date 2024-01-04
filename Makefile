.PHONY: black black-test check clean clean-build clean-pyc clean-test coverage install pylint pylint-quick pyre test publish poetry-check publish isort isort-check


VERSION := `cat VERSION`
package := "ffci"

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.mypy_cache' -exec rm -fr {} +
	find . -name '.pyre' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -f coverage.xml
	rm -f report.xml
test:
	FFCI_CONFIG=tests/data/config.yaml poetry run py.test --cov=$(package) --verbose tests --cov-report=html --cov-report=term --cov-report xml:coverage.xml --cov-report=term-missing --junitxml=report.xml --asyncio-mode=auto

coverage:
	poetry run coverage run --source $(package) setup.py test
	poetry run coverage report -m
	poetry run coverage html
	$(BROWSER) htmlcov/index.html

install: clean
	poetry install

pylint-quick:
	poetry run pylint --rcfile=.pylintrc $(package)  -E -r y

pylint:
	poetry run pylint --rcfile=".pylintrc" $(package)

check: black-test isort-check poetry-check pylint pyre-check

pyre:
	poetry run pyre

pyre-check:
	poetry run pyre --noninteractive check 2>/dev/null

black:
	poetry run black -t py310 tests $(package)

black-test:
	poetry run black -t py310 tests $(package) --check

poetry-check:
	poetry lock --check

publish: clean
	poetry build
	poetry publish

isort:
	poetry run isort .

isort-check:
	poetry run isort --diff --check .

.ONESHELL:
pyrightconfig:
	jq \
      --null-input \
      --arg venv "$$(basename $$(poetry env info -p))" \
      --arg venvPath "$$(dirname $$(poetry env info -p))" \
      '{ "venv": $$venv, "venvPath": $$venvPath }' \
      > pyrightconfig.json

rename:
	ack ffci -l | xargs -i{} sed -r -i "s/ffci/ffci/g" {}
	# ack Hemporalloop -i -l | xargs -i{} sed -r -i "s/Temporalloop/Hub2labhook/g" {}

run-worker:
	poetry run bin/ffci worker --config=localconfig.yaml

run-server:
	poetry run bin/ffci server --config localconfig.yaml
