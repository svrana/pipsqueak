.DEFAULT_GOAL := help

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo " test     run tests"
	@echo " clean	   removes all META-* and egg-info/ files created by build tools"
	@echo " sdist    make a source distribution"
	@echo " bdist    make an egg distribution"
	@echo " install  install package"
	@echo " publish  publish to pypi.python.org"

cleanmeta:
	-rm -rf pipsqueak.egg-info

clean: cleanmeta
	-rm -rf dist
	-rm -rf build
	-find . -type f -name "*.orig" -exec rm -f "{}" \;
	-find . -type f -name "*.rej" -exec rm -f "{}" \;
	-find . -type f -name "*.pyc" -exec rm -f "{}" \;
	-find . -type f -name "*.parse-index" -exec rm -f "{}" \;

sdist: cleanmeta
	python setup.py sdist

bdist: cleanmeta
	python setup.py bdist_egg

install:
	python setup.py install

publish:
	python setup.py sdist upload

test:
	py.test


WATCH_FILES=fd -e .py

entr-warn:
	@echo "-------------------------------------------------"
	@echo " ! File watching functionality non-operational ! "
	@echo "                                                 "
	@echo " Install entr(1) to run tasks on file change.    "
	@echo " See http://entrproject.org/                     "
	@echo "-------------------------------------------------"

watch-test:
	if command -v entr > /dev/null; then ${WATCH_FILES} | \
        entr -c $(MAKE) test; else $(MAKE) test entr-warn; fi

coverage:
	pytest --cov=./

.PHONY: help,cleanmeta,clean,sdist,bdist,install,publish,test,entr-warn,watch-test,coverage
