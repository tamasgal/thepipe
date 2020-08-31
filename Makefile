PKGNAME=thepipe

default: build

all: install

install: 
	pip install .

install-dev:
	pip install -e ".[dev]"

test: 
	py.test $(PKGNAME)

test-cov:
	py.test --cov=$(PKGNAME)

test-loop: 
	py.test $(PKGNAME)
	ptw --ext=.py,.pyx --ignore=doc $(PKGNAME)

yapf:
	yapf -i -r $(PKGNAME)
	yapf -i setup.py

.PHONY: all clean install install-dev test yapf
