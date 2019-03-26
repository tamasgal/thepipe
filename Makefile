PKGNAME=thepipe

default: build

all: install

install: 
	pip install .

install-dev:
	pip install -e .

test: 
	py.test --junitxml=./reports/junit.xml $(PKGNAME)

test-cov:
	py.test --cov ./ --cov-report term-missing --cov-report xml:reports/coverage.xml --cov-report html:reports/coverage $(PKGNAME)

test-loop: 
	py.test $(PKGNAME)
	ptw --ext=.py,.pyx --ignore=doc $(PKGNAME)

flake8: 
	py.test --flake8

pep8: flake8

docstyle: 
	py.test --docstyle

lint: 
	py.test --pylint

dependencies:
	pip install -Ur requirements.txt

.PHONY: yapf
yapf:
	yapf -i -r $(PKGNAME)
	yapf -i setup.py

.PHONY: all clean install install-dev test flake8 pep8 dependencies lint yapf
