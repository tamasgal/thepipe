PKGNAME=thepipe

default: build

all: install

install: 
	pip install .

install-dev:
	pip install -Ur requirements/dev.txt
	pip install -e .

test: 
	py.test $(PKGNAME)

test-cov:
	py.test --cov=$(PKGNAME)

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
	pip install -Ur requirements/install.txt

.PHONY: yapf
yapf:
	yapf -i -r $(PKGNAME)
	yapf -i setup.py

.PHONY: all clean install install-dev test flake8 pep8 dependencies lint yapf
