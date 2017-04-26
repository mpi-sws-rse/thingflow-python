# Makefile for antevents - just a simple wrapper over shell commands

help:
	@echo "make targets are: dist tests clean help"

dist:
	python3 setup.py sdist
	python3 setup.py bdist_wheel

tests:
	cd tests; ./runtests.sh

clean:
	rm -f MANIFEST
	rm -rf dist/ build/
	rm -rf antevents.egg-info/
	find . -name '*~' -delete
	rm -rf tests/*.err tests/*.out

.PHONY: help dist tests clean
