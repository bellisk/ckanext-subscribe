# encoding: utf-8

import datetime

from nose.tools import assert_equal

from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import get_notifications
from ckanext.subscribe.tests import factories

eq = assert_equal


class TestGetNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10)
        )
        _, _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'])

        notifies = get_notifications()

        eq([notify['subscription']['email'] for notify in notifies],
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'new package', dataset['id'], [u'package'])])

    def test_old_activity_not_notified(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=70))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_just_occurred_not_notified(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=1))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_notifications()

        eq(_get_activities(notifies), [])


def _get_activities(notifications):
    activities = []
    for notification in notifications:
        for activity in notification['activities']:
            activities.append((
                activity['activity_type'],
                activity['object_id'],
                activity['data'].keys()))
    return activities
