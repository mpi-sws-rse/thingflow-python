# Makefile for antevents - just a simple wrapper over shell commands

help:
	@echo "make targets are: sdist tests clean help"

sdist:
	python3 setup.py sdist

tests:
	cd tests; ./runtests.sh

clean:
	rm -f MANIFEST
	rm -rf dist/
	rm -rf antevents.egg-info
	find . -name '*~' -delete

.PHONY: help sdist tests clean
