.PHONY: clean-pyc clean-build docs clean test test-all
define BROWSER_PYSCRIPT
import os, webbrowser, sys
try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT
BROWSER := python -c "$$BROWSER_PYSCRIPT"
VERSION = `cat VERSION`

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

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/


.virtenv/.date: requirements_dev.txt requirements_test.txt requirements.txt
	virtualenv -p python3.6 $(shell dirname $@)
	. $(shell dirname $@)/bin/activate && for f in $<; do pip install -r $$f; done && pip install -e .
	touch -r $< $@

test-env-setup: .virtenv/.date
	@echo "To use the provided virtual environment: \n\tsource $(shell dirname $<)/bin/activate && make test"

lint:
	flake8 hub2lab-hook tests

test:
	py.test --cov=hub2labhook --cov-report=html --cov-report=term-missing  --verbose tests

test-all:
	py.test --cov=hub2labhook --cov-report=html --cov-report=term-missing  --verbose tests

tox:
	tox

coverage:
	coverage run --source hub2lab-hook setup.py test
	coverage report -m
	coverage html
	$(BROWSER) htmlcov/index.html

docs: install
	rm -f test1
	sphinx-apidoc  -f -P -o docs/test1 hub2lab-hook
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	$(BROWSER) docs/_build/html/index.html

servedocs: docs
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

gen-config:
	python scripts/generate-conf-doc.py > Documentation/config/failfast-ci.yaml

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean
	python setup.py install

flake8:
	python setup.py flake8

coveralls: test
	coveralls

pylint:
	pylint --rcfile=".pylintrc" hub2labhook -E -r y

pylint-all:
	pylint --rcfile=".pylintrc" hub2labhook

yapf:
	yapf -r hub2labhook -i

yapf-diff:
	yapf -r hub2labhook -d

yapf-test: yapf-diff
	if [ `yapf -r hub2labhook -d | wc -l` -gt 0 ] ; then false ; else true ;fi


dockerfile: clean dist
	tar xvf dist/hub2lab-hook-${VERSION}.tar.gz -C dist
	git rev-parse HEAD > dist/GIT_HEAD
	docker build --build-arg version=$(VERSION) -f Dockerfile -t quay.io/failfast-ci/failfast:v$(VERSION) .

dockerfile-canary: clean
	docker build -t quay.io/failfast-ci/failfast:master .
	docker push quay.io/failfast-ci/failfast:master

dockerfile-push: dockerfile
	docker push quay.io/failfast-ci/failfast:v$(VERSION)

fmt-ci:
	find . -iname "*.jsonnet" | xargs jsonnet fmt -i -n 2
	find . -iname "*.libsonnet" | xargs jsonnet fmt -i -n 2

gen-ci:
	ffctl gen

mypy:
	mypy hub2labhook --ignore-missing-imports

check: pylint flake8 mypy yapf-test gen-ci gen-config

prepare: yapf gen-ci check
