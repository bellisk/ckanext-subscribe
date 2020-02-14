# encoding: utf-8

import datetime

import mock
from nose.tools import assert_equal, assert_in

from ckan.tests import helpers
from ckan.tests.factories import Dataset, Organization, Group
from ckan import model

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.model import Frequency
from ckanext.subscribe.notification import (
    send_any_immediate_notifications,
    get_immediate_notifications,
    send_weekly_notifications_if_its_time_to,
    get_weekly_notifications,
    send_daily_notifications_if_its_time_to,
    get_daily_notifications,
    send_emails,
    dictize_notifications,
    most_recent_weekly_notification_datetime,
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
        dataset = factories.DatasetActivity()
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
        assert time_since_emails_last_sent(Frequency.IMMEDIATE.value) \
            < datetime.timedelta(seconds=1)


class TestGetImmediateNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()
        subscribe_notification._config = {}

    def test_basic(self):
        dataset = factories.DatasetActivity()
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(notifies.keys(),
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_subscribe_to_an_org_and_its_dataset_has_activity(self):
        org = Organization()
        subscription = factories.Subscription(organization_id=org['id'])
        subscribe_model.Subscribe.set_emails_last_sent(
            Frequency.IMMEDIATE.value,
            datetime.datetime.now())
        dataset = Dataset(owner_org=org['id'])

        notifies = get_immediate_notifications()

        eq(notifies.keys(),
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_subscribe_to_an_group_and_its_dataset_has_activity(self):
        group = Group()
        subscription = factories.Subscription(group_id=group['id'])
        subscribe_model.Subscribe.set_emails_last_sent(
            Frequency.IMMEDIATE.value,
            datetime.datetime.now())
        dataset = Dataset(groups=[{'id': group['id']}])

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

    def test_activity_already_notified_not_notified_again(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        subscribe_model.Subscribe.set_emails_last_sent(
            Frequency.IMMEDIATE.value,
            datetime.datetime.now() - datetime.timedelta(minutes=5))
        model.Session.commit()
        factories.Subscription(dataset_id=dataset['id'])

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])

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

    def test_weekly_frequency_subscriptions_are_not_included(self):
        dataset = factories.DatasetActivity()
        factories.Subscription(dataset_id=dataset['id'], frequency='weekly')

        notifies = get_immediate_notifications()

        eq(_get_activities(notifies), [])


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


class TestSendWeeklyNotificationsIfItsTimeTo(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_basic(self, send_notification_email):
        dataset = factories.DatasetActivity()
        subscription = factories.Subscription(dataset_id=dataset['id'],
                                              frequency='weekly')

        send_weekly_notifications_if_its_time_to()

        send_notification_email.assert_called_once()
        code, email, notifications = send_notification_email.call_args[0]
        eq(type(code), type(u''))
        eq(email, 'bob@example.com')
        eq(len(notifications), 1)
        eq([(a['activity_type'], a['data']['package']['id'])
            for a in notifications[0]['activities']],
           [('new package', dataset['id'])])
        eq(notifications[0]['subscription']['id'], subscription['id'])
        assert time_since_emails_last_sent(Frequency.WEEKLY.value) \
            < datetime.timedelta(seconds=1)

    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_no_emails_to_send_but_week_is_marked_done(self, send_notification_email):

        send_weekly_notifications_if_its_time_to()

        send_notification_email.assert_not_called()
        assert time_since_emails_last_sent(Frequency.WEEKLY.value) \
            < datetime.timedelta(seconds=1)


class TestGetWeeklyNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()
        subscribe_notification._config = {}

    def test_basic(self):
        dataset = factories.DatasetActivity()
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'],
                                              frequency='weekly')

        notifies = get_weekly_notifications()

        eq(notifies.keys(),
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_daily_frequency_subscriptions_are_not_included(self):
        dataset = factories.DatasetActivity()
        factories.Subscription(dataset_id=dataset['id'], frequency='daily')

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])

    def test_daily_frequency_subscriptions_of_an_org_are_not_included(self):
        org = Organization()
        factories.Subscription(organization_id=org['id'],
                               frequency='daily')
        Dataset(owner_org=org['id'])

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])

    def test_immediate_frequency_subscriptions_are_not_included(self):
        dataset = factories.DatasetActivity()
        factories.Subscription(dataset_id=dataset['id'], frequency='immediate')

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])

    def test_immediate_frequency_subscriptions_of_an_group_are_not_included(self):
        group = Group()
        factories.Subscription(group_id=group['id'],
                               frequency='immediate')
        Dataset(groups=[{'id': group['id']}])

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])

    def test_activities_older_than_a_week_are_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(days=8))
        factories.Subscription(dataset_id=dataset['id'],
                               frequency='weekly')

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])

    def test_activities_already_notified_are_not_notified_again(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(days=1))
        factories.Subscription(dataset_id=dataset['id'],
                               frequency='weekly')
        subscribe_model.Subscribe.set_emails_last_sent(
            frequency=Frequency.WEEKLY.value,
            emails_last_sent=datetime.datetime.now())
        model.Session.commit()

        notifies = get_weekly_notifications()

        eq(_get_activities(notifies), [])


class TestSendDailyNotificationsIfItsTimeTo(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_basic(self, send_notification_email):
        dataset = factories.DatasetActivity()
        subscription = factories.Subscription(dataset_id=dataset['id'],
                                              frequency='daily')

        send_daily_notifications_if_its_time_to()

        send_notification_email.assert_called_once()
        code, email, notifications = send_notification_email.call_args[0]
        eq(type(code), type(u''))
        eq(email, 'bob@example.com')
        eq(len(notifications), 1)
        eq([(a['activity_type'], a['data']['package']['id'])
            for a in notifications[0]['activities']],
           [('new package', dataset['id'])])
        eq(notifications[0]['subscription']['id'], subscription['id'])
        assert time_since_emails_last_sent(Frequency.DAILY.value) \
            < datetime.timedelta(seconds=1)

    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_no_emails_to_send_but_day_is_marked_done(self, send_notification_email):

        send_daily_notifications_if_its_time_to()

        send_notification_email.assert_not_called()
        assert time_since_emails_last_sent(Frequency.DAILY.value) \
            < datetime.timedelta(seconds=1)


class TestGetDailyNotifications(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()
        subscribe_notification._config = {}

    def test_basic(self):
        dataset = factories.DatasetActivity()
        _ = factories.DatasetActivity()  # decoy
        subscription = factories.Subscription(dataset_id=dataset['id'],
                                              frequency='daily')

        notifies = get_daily_notifications()

        eq(notifies.keys(),
           [subscription['email']])
        eq(_get_activities(notifies),
           [(u'bob@example.com', u'new package', dataset['id'])])

    def test_weekly_frequency_subscriptions_are_not_included(self):
        dataset = factories.DatasetActivity()
        factories.Subscription(dataset_id=dataset['id'], frequency='weekly')

        notifies = get_daily_notifications()

        eq(_get_activities(notifies), [])

    def test_immediate_frequency_subscriptions_are_not_included(self):
        dataset = factories.DatasetActivity()
        factories.Subscription(dataset_id=dataset['id'], frequency='immediate')

        notifies = get_daily_notifications()

        eq(_get_activities(notifies), [])

    def test_activities_older_than_a_day_are_not_notified(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(hours=25))
        factories.Subscription(dataset_id=dataset['id'],
                               frequency='daily')

        notifies = get_daily_notifications()

        eq(_get_activities(notifies), [])

    def test_activities_already_notified_are_not_notified_again(self):
        dataset = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(hours=1))
        factories.Subscription(dataset_id=dataset['id'],
                               frequency='daily')
        subscribe_model.Subscribe.set_emails_last_sent(
            frequency=Frequency.DAILY.value,
            emails_last_sent=datetime.datetime.now())
        model.Session.commit()

        notifies = get_daily_notifications()

        eq(_get_activities(notifies), [])


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


class TestMostRecentWeeklyNotification(object):

    def test_earlier_that_week(self):
        eq(most_recent_weekly_notification_datetime(
               datetime.datetime(2020, 1, 25)),  # a saturday
           datetime.datetime(2020, 1, 24, 9, 0))

    def test_later_that_week(self):
        eq(most_recent_weekly_notification_datetime(
               datetime.datetime(2020, 1, 23)),  # a thursday
           datetime.datetime(2020, 1, 17, 9, 0))

    def test_same_day_of_week_earlier_in_the_day(self):
        eq(most_recent_weekly_notification_datetime(
               datetime.datetime(2020, 1, 24, 8, 0)),  # a friday
           datetime.datetime(2020, 1, 17, 9, 0))

    def test_same_day_of_week_later_in_the_day(self):
        eq(most_recent_weekly_notification_datetime(
               datetime.datetime(2020, 1, 24, 10, 0)),  # a friday
           datetime.datetime(2020, 1, 24, 9, 0))


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


def time_since_emails_last_sent(frequency):
    return (datetime.datetime.now() -
            subscribe_model.Subscribe.get_emails_last_sent(frequency))
