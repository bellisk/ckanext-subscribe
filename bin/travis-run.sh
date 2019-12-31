#!/bin/sh -e
set -ex

flake8 --version
# stop the build if there are Python syntax errors or undefined names
flake8 . --count --select=E901,E999,F821,F822,F823 --show-source --statistics --exclude ckan,ckanext-subscribe

nosetests --ckan \
          --nologcapture \
          --with-pylons=subdir/test.ini \
          --with-coverage \
          --cover-package=ckanext.subscribe \
          --cover-inclusive \
          --cover-erase
