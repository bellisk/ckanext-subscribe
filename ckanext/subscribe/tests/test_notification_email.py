# encoding: utf-8

import datetime

import mock
from nose.tools import assert_equal, assert_in

from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import dictize_notifications
from ckanext.subscribe.notification_email import (
    send_notification_email,
    get_notification_email_contents,
    get_notification_email_vars,
)
from ckanext.subscribe.tests import factories

eq = assert_equal


class TestSendNotificationEmail(object):

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
        notifications = dictize_notifications(subscription_activities)

        send_notification_email(
            code='the-code', email='bob@example.com',
            notifications=notifications)

        mail_recipient.assert_called_once()
        body = mail_recipient.call_args[1]['body']
        print(body)
        assert_in(dataset['title'], body)
        assert_in('http://test.ckan.net/dataset/{}'.format(dataset['id']), body)
        assert_in('new dataset', body)
        body = mail_recipient.call_args[1]['body_html']
        print(body)
        assert_in(dataset['title'], body)
        assert_in('http://test.ckan.net/dataset/{}'.format(dataset['id']), body)
        assert_in('new dataset', body)


class TestGetNotificationEmailContents(object):

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
        notifications = dictize_notifications(subscription_activities)

        get_notification_email_contents(
            code='the-code', email='bob@example.com',
            notifications=notifications)

        # just check there are no exceptions


class TestGetNotificationEmailVars(object):

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
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        eq(email_vars['notifications'],
           [{'activities': [{'activity_type': u'new dataset',
                             'timestamp': activity.timestamp}],
             'object_link': 'http://test.ckan.net/dataset/{}'.format(dataset['id']),
             'object_name': dataset['name'],
             'object_title': dataset['title'],
             'object_type': u'dataset'}]
           )

    def test_group(self):
        group, activity = factories.GroupActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(group_id=group['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        eq(email_vars['notifications'],
           [{'activities': [{'activity_type': u'new group',
                             'timestamp': activity.timestamp}],
             'object_link': 'http://test.ckan.net/group/{}'.format(group['id']),
             'object_name': group['name'],
             'object_title': group['title'],
             'object_type': u'group'}]
           )

    def test_org(self):
        org, activity = factories.OrganizationActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(organization_id=org['id'],
                                   return_object=True):
            [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            email='bob@example.com',
            notifications=notifications)

        eq(email_vars['notifications'],
           [{'activities': [{'activity_type': u'new organization',
                             'timestamp': activity.timestamp}],
             'object_link': 'http://test.ckan.net/organization/{}'.format(org['id']),
             'object_name': org['name'],
             'object_title': org['title'],
             'object_type': u'organization'}]
           )
