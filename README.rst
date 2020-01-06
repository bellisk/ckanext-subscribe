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

Compatibility with core CKAN versions:

=============== =============
CKAN version    Compatibility
=============== =============
2.6 and earlier no
2.7             yes
2.8             yes
2.9             not yet
=============== =============

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

   Note: This causes python packages 'rq-scheduler', 'rq' and 'redis' to be
   installed or upgraded.

3. Add ``subscribe`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Initialize the subscribe tables in the database::

     paster --plugin=ckanext-subscribe subscribe initdb

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

6. You need to run the 'send-any-notifications' command regularly. You can see
   it running on the command-line::

     paster --plugin=ckanext-subscribe subscribe send-any-notifications -c=/etc/ckan/default/development.ini

   But you'll probably want a cron job setup to run it every minute or so.
   We're going to edit the cron table -
   development machine just do this for your user:

     crontab -e

   Or a production machine use the 'ckan' user, instead of checking for notifications on the
   command-line, create CRON job. To do so, edit the cron table with the
   following command (it may ask you to choose an editor)::

     sudo crontab -e -u ckan

   Paste this line into your crontab, again replacing the paths to paster and the ini file with yours:

     # m h  dom mon dow   command
     *   *  *   *   *     /usr/lib/ckan/default/bin/paster --plugin=ckanext-subscribe subscribe run --config=/etc/ckan/default/production.ini

   This particular example will check for notifications every minute.


---------------
Config settings
---------------

# The queue name for the background jobs that send the notification emails.
# Defaults to the CKAN queue, which is the default for the worker to process.
# See: https://docs.ckan.org/en/latest/maintaining/background-tasks.html#background-job-queues
# (optional, default: ckan:default:default).
ckanext.subscribe.queue = ckan:default:default

# Delay sending notification emails until after a grace period, in case there
# are further changes. When further changes occur, the grace period is extended
# to this period after the latest change. However there is also a maximum grace
# period, after which the notification will be sent, no matter if there are
# further changes to the object subcribed to.
# Applies only to subscriptions which are set to frequency 'continuous'.
# The default values are shown. If you set these to 0, it will send
# notifications as soon as a change is made (well, as soon as
# send-any-notifications is called next).
# Units: minutes
ckanext.subscribe.continuous_notification_grace_period_minutes = 5
ckanext.subscribe.continuous_notification_grace_period_max_minutes = 60

# After a pause in the sending of emails, when it restarts it ignores activity
# older than the catch-up period.
# Units: hours
ckanext.subscribe.catch_up_period_hours = 24

---------------
Troubleshooting
---------------

**Notification emails not being sent**

1. Check your cron schedule is working: TODO

1. Create a test activity for a dataset/group/org you are subscribed to::

     paster --plugin=ckanext-subscribe subscribe create-test-activity mydataset

   You should in the worker log the email being sent::

     2020-01-06 16:30:40,591 DEBUG [ckanext.subscribe.notification] do_continuous_notifications
     2020-01-06 16:30:40,628 DEBUG [ckanext.subscribe.notification] sending 1 emails (continuous frequency)
     2020-01-06 16:30:42,116 INFO  [ckanext.subscribe.mailer] Sent email to david.read@hackneyworkshop.com

1. Clean up all test activity afterwards (it is visible to users in the
   activity stream)::

     paster --plugin=ckanext-subscribe subscribe delete-test-activity


**NameError: global name 'Subscription' is not defined**

You need to initialize the subscribe tables in the database.  See
'Installation' section above to do this.


**KeyError: "Action 'subscribe_signup' not found"**

You need to enable the `subscribe` plugin in your CKAN config. See
'Installation' section above to do this.


**ProgrammingError: (ProgrammingError) relation "subscription" does not exist**

You're running the tests with `--reset-db` and this extension doesn't work with
that. Instead, if you need to wipe the tables before running tests, do it this
way::

    sudo -u postgres psql ckan_test -c 'drop table if exists subscription; drop table if exists subscribe_login_code;'


----------------------
Developer installation
----------------------

To install ckanext-subscribe for development, activate your CKAN virtualenv and
do::

    git clone https://github.com/davidread/ckanext-subscribe.git
    cd ckanext-subscribe
    python setup.py develop
    pip install -r dev-requirements.txt

Now continue Installation steps from step 3


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
