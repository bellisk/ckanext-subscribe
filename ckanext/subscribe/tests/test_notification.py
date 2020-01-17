# encoding: utf-8

import datetime

import mock
from nose.tools import assert_equal, assert_in

from ckan.tests import helpers
from ckan.tests.factories import Dataset

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import (
    send_any_immediate_notifications,
    get_immediate_notifications,
    send_emails,
    dictize_notifications,
)
from ckanext.subscribe import notification as subscribe_notification
from ckanext.subscribe.tests import factories

eq = assert_equal


class TestSendAnyImmediateNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_basic(self, send_notification_email):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10)
        )
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'])

        send_any_immediate_notifications()

        send_notification_email.assert_called_once()
        code, email, notifications = send_notification_email.call_args[0]
        eq(type(code), type(u''))
        eq(email, 'bob@example.com')
        eq(len(notifications), 1)
        eq([(a['activity_type'], a['data']['package']['id'])
            for a in notifications[0]['activities']],
           [('new package', dataset['id'])])
        eq(notifications[0]['subscription']['id'], subscription['id'])
        assert time_since_emails_last_sent() < datetime.timedelta(seconds=1)


class TestGetImmediateNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()
        subscribe_notification._config = {}

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

    @helpers.change_config(
        'ckanext.subscribe.immediate_notification_grace_period_minutes', '5')
    def test_activity_just_occurred_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=1))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    @helpers.change_config(
        'ckanext.subscribe.immediate_notification_grace_period_minutes', '5')
    def test_activity_not_notified_yet_as_more_activity(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package',
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=2))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    @helpers.change_config(
        'ckanext.subscribe.immediate_notification_grace_period_minutes', '5')
    def test_activity_already_notified_not_notified_again(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        subscribe_model.Subscribe.set_emails_last_sent(
            datetime.datetime.now() - datetime.timedelta(minutes=5))
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

    @helpers.change_config(
        'ckanext.subscribe.immediate_notification_grace_period_minutes', '0')
    def test_activity_before_the_subscription_is_not_notified(self):
        dataset = Dataset()
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package')
        factories.Subscription(dataset_id=dataset['id'],
                               created=datetime.datetime.now())
        factories.Activity(
            object_id=dataset['id'], activity_type='changed package')

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [
            (u'bob@example.com', u'changed package', dataset['id'])
        ])

    def test_lots_of_users_and_datasets(self):
        datasetx = _create_dataset_and_activity([70, 50, 10])
        datasety = _create_dataset_and_activity([40, 20])
        _ = factories.DatasetActivity()  # decoy
        factories.Subscription(
            email='user@a.com', dataset_id=datasetx['id'],
            created=datetime.datetime.now() - datetime.timedelta(hours=2))
        factories.Subscription(
            email='user@b.com', dataset_id=datasetx['id'],
            created=datetime.datetime.now() - datetime.timedelta(hours=2))
        factories.Subscription(
            email='user@b.com', dataset_id=datasety['id'],
            created=datetime.datetime.now() - datetime.timedelta(hours=2))

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


def time_since_emails_last_sent():
    return (datetime.datetime.now() -
            subscribe_model.Subscribe.get_emails_last_sent())
