.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org/davidread/ckanext-subscribe.svg?branch=master
    :target: https://travis-ci.org/davidread/ckanext-subscribe

.. image:: https://coveralls.io/repos/davidread/ckanext-subscribe/badge.svg
  :target: https://coveralls.io/r/davidread/ckanext-subscribe

.. image:: https://img.shields.io/pypi/v/ckanext-subscribe.svg
    :target: https://pypi.org/project/ckanext-subscribe/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/ckanext-subscribe.svg
    :target: https://pypi.org/project/ckanext-subscribe/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/status/ckanext-subscribe.svg
    :target: https://pypi.org/project/ckanext-subscribe/
    :alt: Development Status

.. image:: https://img.shields.io/pypi/l/ckanext-subscribe.svg
    :target: https://pypi.org/project/ckanext-subscribe/
    :alt: License

=================
ckanext-subscribe
=================

CKAN extension that allows users to subscribe to dataset/organization/group
updates WITHOUT requiring them to login.

This feature is complementary to CKAN's existing "Follow" feature, which allows
logged in users to subscribe to get update emails. Log-in can be a barrier to
casual interest in say a handful of datasets. Generating and storing a password
is a burden on the user, and for casual use just using temporary email links,
as in this extension, is more appropriate.

------------
Requirements
------------

Designed for CKAN 2.7+

------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-subscribe:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-subscribe Python package into your virtual environment::

     pip install ckanext-subscribe

3. Add ``subscribe`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Initialize the subscribe tables in the database::

     paster --plugin=ckanext-subscribe subscribe initdb

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload


---------------
Config settings
---------------

None at present

.. Document any optional config settings here. For example::

.. # The minimum number of hours to wait before re-checking a resource
   # (optional, default: 24).
   ckanext.subscribe.some_setting = some_default_value


----------------------
Developer installation
----------------------

To install ckanext-subscribe for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/davidread/ckanext-subscribe.git
    cd ckanext-subscribe
    python setup.py develop
    pip install -r dev-requirements.txt


-----
Tests
-----

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.subscribe --cover-inclusive --cover-erase --cover-tests


--------------------------------------------
Releasing a new version of ckanext-subscribe
--------------------------------------------

ckanext-subscribe should be available on PyPI as https://pypi.org/project/ckanext-subscribe.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Make sure you have the latest version of necessary packages::

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version::

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI::

       twine upload dist/*

5. Commit any outstanding changes::

       git commit -a

6. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags
