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

4. Initialize the subscribe tables in the database and create the schedule for
   sending emails::

     paster --plugin=ckanext-subscribe subscribe init

   Note the schedule is stored as an RQ job, so if you clear jobs then you'll
   need to re-initialize this schedule.

5. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

6. Ensure CKAN's background tasks worker is running. First test it on the
   command-line::

     paster --plugin=ckan jobs worker -c=/etc/ckan/default/development.ini

   You can leave that running for development purposes. Or for production, run
   it automatically by using supervisor. For more information, see:
   <https://docs.ckan.org/en/2.8/maintaining/background-tasks.html#running-background-jobs>

7. Setup the RQ Scheduler. First test it on the command-line::

     python /usr/lib/ckan/default/local/lib/python2.7/site-packages/rq_scheduler/scripts/rqscheduler.py -i 10 -v

   Create a config file by running::

     echo "[Unit]
     Description=RQScheduler
     After=network.target

     [Service]
     ExecStart=/usr/lib/ckan/default/bin/python \
        /usr/lib/ckan/default/local/lib/python2.7/site-packages/rq_scheduler/scripts/rqscheduler.py

     [Install]
     WantedBy=multi-user.target" | sudo tee /etc/systemd/system/rqscheduler.service

   Start it::

     sudo systemctl start rqscheduler.service

   Configure it to start every boot::

     sudo systemctl enable rqscheduler.service

   You can also check it::

     sudo systemctl status rqscheduler.service


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
# notifications as soon as a change is made (subject to waiting for the regular
# running of rqscheduler and continuous_notification_poll_interval_seconds
# setting).
# Units: minutes
ckanext.subscribe.continuous_notification_grace_period_minutes = 5
ckanext.subscribe.continuous_notification_grace_period_max_minutes = 60

# Interval between checks for activity, and therefore potentially sending
# notifications.
# NB when you adjust this setting, for it to take effect you need to
# reinitialize the scheduler by running:
#     paster --plugin=ckanext-subscribe subscribe scheduler init
# Note: if the value is less than 60s then you'll also need to decrease the
# interval that rqscheduler.py runs (e.g. "-i 30"), because it defaults to 60s.
# Units: seconds
ckanext.subscribe.continuous_notification_poll_interval_seconds = 60

---------------
Troubleshooting
---------------

**Notification emails not being sent**

1. Check your schedule is initialized (this can be wiped if you clear
Background Jobs). To ensure it is initialized::

    paster --plugin=ckanext-subscribe subscribe scheduler init

   Check the interval (in seconds)

1. Check the RQ Scheduler is running::

     sudo systemctl status rqscheduler.service

   It should be::

      Active: active (running)

1. Check the RQ Scheduler logs::

      sudo journalctl -u rqscheduler.service -f

   It should show::

      Jan 06 16:51:34 ubuntu-xenial python[24487]: 16:51:34 Registering birth

   What's useful is to add to the (ExecStart) the commandline option `-v` to
   see the scheduling every minute::

     Jan 06 16:52:45 ubuntu-xenial python[24584]: 16:52:45 Entering run loop
     Jan 06 16:52:45 ubuntu-xenial python[24584]: 16:52:45 Checking for scheduled jobs
     Jan 06 16:52:45 ubuntu-xenial python[24584]: 16:52:45 Pushing 956161f2-9a3b-4af3-98a8-d1392840303a to ckan:default:default
     Jan 06 16:52:45 ubuntu-xenial python[24584]: 16:52:45 Sleeping 60.00 seconds

   If the 'Pushing' line is missing, it's because the schedule is not
   initialized or not ready to be queued yet - compare with the "enqueued_at"
   value of the schedule.

1. If your worker is run with supervisor, check it is running:

     sudo supervisorctl status

1. Check your worker log. If you're developing it may be running in a terminal
   with `paster --plugin=ckan jobs worker` or if it is running with
   supervisor, follow it like this::

     tail -f /var/log/ckan-worker.log

   Every interval You should get logs like this::

     2020-01-06 16:31:30,025 INFO  [rq.worker] ckan:default:default: ckanext.subscribe.notification.do_continuous_notifications() (956161f2-9a3b-4af3-98a8-d1392840303a)
     2020-01-06 16:31:30,509 DEBUG [ckanext.subscribe.notification] do_continuous_notifications
     2020-01-06 16:31:30,520 DEBUG [ckanext.subscribe.notification] no emails to send (continuous frequency)

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
