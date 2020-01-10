# encoding: utf-8

import datetime

import mock
from nose.tools import assert_equal, assert_in

from ckan.tests import helpers
from ckan import model

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import (
    get_immediate_notifications,
    send_emails,
    dictize_notifications,
    record_activities_notified,
)
from ckanext.subscribe.tests import factories

eq = assert_equal


class TestGetImmediateNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_basic(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10)
        )
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(notifies.keys(),
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_old_activity_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(hours=49))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_just_occurred_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=1))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_not_notified_yet_as_more_activity(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package',
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=2))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    def test_activity_already_notified_not_notified_again(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True)
        factories.ActivityNotified(activity_id=activity.id)
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

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

        notifies = get_immediate_notifications()

        eq(set(notifies.keys()),
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


def _get_activities(notifications_by_email):
    activities = []
    for email, notifications in notifications_by_email.items():
        for notification in notifications:
            for activity in notification['activities']:
                activities.append((
                    email,
                    activity['activity_type'],
                    activity['object_id'],
                    ))
    return activities


class TestSendEmails(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_basic(self, mail_recipient):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity]
        }
        notifications_by_email = {
            'bob@example.com': dictize_notifications(subscription_activities)
        }

        send_emails(notifications_by_email)

        mail_recipient.assert_called_once()
        body = mail_recipient.call_args[1]['body']
        print(body)
        assert_in('new dataset', body)


class TestRecordActivitiesNotified(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity]
        }

        notifications_by_email = {
            'bob@example.com': dictize_notifications(subscription_activities)
        }

        record_activities_notified(notifications_by_email)

        activites_notified = \
            model.Session.query(subscribe_model.ActivityNotified.activity_id) \
            .all()
        eq(activites_notified, [(activity.id,)])

    def test_two_activities(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        activity2 = factories.Activity(
            object_id=dataset['id'], activity_type='changed package',
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=9),
            return_object=True)

        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset['id'],
                                   return_object=True):
            [activity, activity2]
        }

        notifications_by_email = {
            'bob@example.com': dictize_notifications(subscription_activities)
        }

        record_activities_notified(notifications_by_email)

        activities_notified = \
            model.Session.query(subscribe_model.ActivityNotified.activity_id) \
            .all()
        eq(set((a[0] for a in activities_notified)),
           set((activity.id, activity2.id)))

    def test_deletes_activities_from_before_the_catch_up_period(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(days=2),
            return_activity=True)
        factories.ActivityNotified(
            activity_id=activity.id,
            timestamp=datetime.datetime.now() - datetime.timedelta(days=2))

        record_activities_notified({'bob@example.com': []})

        activities_notified = \
            model.Session.query(subscribe_model.ActivityNotified.activity_id) \
            .all()
        eq(activities_notified, [])
