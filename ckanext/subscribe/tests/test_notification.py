# encoding: utf-8

import datetime

from nose.tools import assert_equal

from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import get_real_time_notifications
from ckanext.subscribe.tests import factories

eq = assert_equal


class TestGetRealTimeNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_basic(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10)
        )
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'])

        notifies = get_real_time_notifications()

        eq([notify['subscription']['email'] for notify in notifies],
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_old_activity_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=70))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_real_time_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_just_occurred_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=1))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_real_time_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_not_notified_yet_as_more_activity(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package',
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=2))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_real_time_notifications()

        eq(_get_activities(notifies), [])

    def test_lots_of_users_and_datasets(self):
        datasetx = _create_dataset_and_activity([70, 50, 10])
        datasety = _create_dataset_and_activity([40, 20])
        _ = factories.DatasetActivity()  # decoy
        factories.Subscription(
            email='user@a.com', dataset_id=datasetx['id'])
        factories.Subscription(
            email='user@b.com', dataset_id=datasetx['id'])
        factories.Subscription(
            email='user@b.com', dataset_id=datasety['id'])

        notifies = get_real_time_notifications()

        eq(set(notify['subscription']['email'] for notify in notifies),
           set(('user@a.com', 'user@b.com', 'user@b.com')))
        from pprint import pprint
        pprint(_get_activities(notifies))
        eq(set(_get_activities(notifies)),
           set((
                (u'user@a.com', u'new package', datasetx['id']),
                (u'user@a.com', u'changed package', datasetx['id']),
                (u'user@a.com', u'changed package', datasetx['id']),
                (u'user@b.com', u'new package', datasetx['id']),
                (u'user@b.com', u'changed package', datasetx['id']),
                (u'user@b.com', u'changed package', datasetx['id']),
                (u'user@b.com', u'new package', datasety['id']),
                (u'user@b.com', u'changed package', datasety['id']),
               )))


def _create_dataset_and_activity(activity_in_minutes_ago=[]):
    minutes_ago = activity_in_minutes_ago.pop(0)
    dataset = factories.DatasetActivity(
        timestamp=datetime.datetime.now() -
        datetime.timedelta(minutes=minutes_ago))

    while activity_in_minutes_ago:
        minutes_ago = activity_in_minutes_ago.pop(0)
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package',
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=50))
    return dataset


def _get_activities(notifications):
    activities = []
    for notification in notifications:
        for activity in notification['activities']:
            activities.append((
                notification['subscription']['email'],
                activity['activity_type'],
                activity['object_id'],
                ))
    return activities
