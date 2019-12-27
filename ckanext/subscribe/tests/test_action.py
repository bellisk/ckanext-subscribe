# encoding: utf-8

import mock
from nose.tools import assert_equal as eq
from nose.tools import assert_raises, assert_in

from ckan.tests import helpers, factories
from ckan.plugins.toolkit import ValidationError
from ckanext.subscribe.tests.factories import Subscription


class TestSubscribeSignup(object):
    def setup(self):
        helpers.reset_db()

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_basic(self, send_confirmation_email):
        dataset = factories.Dataset()

        subscription = helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            dataset_id=dataset["id"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'dataset')
        eq(send_confirmation_email.call_args[0][0].object_id, dataset['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')
        eq(subscription['object_type'], 'dataset')
        eq(subscription['object_id'], dataset['id'])
        eq(subscription['email'], 'bob@example.com')
        eq(subscription['verified'], False)

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_dataset_name(self, send_confirmation_email):
        dataset = factories.Dataset()

        helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            dataset_id=dataset["name"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'dataset')
        eq(send_confirmation_email.call_args[0][0].object_id, dataset['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_group_id(self, send_confirmation_email):
        group = factories.Group()

        helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            group_id=group["id"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'group')
        eq(send_confirmation_email.call_args[0][0].object_id, group['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_group_name(self, send_confirmation_email):
        group = factories.Group()

        helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            group_id=group["name"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'group')
        eq(send_confirmation_email.call_args[0][0].object_id, group['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_org_id(self, send_confirmation_email):
        org = factories.Organization()

        helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            group_id=org["id"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'organization')
        eq(send_confirmation_email.call_args[0][0].object_id, org['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_org_name(self, send_confirmation_email):
        org = factories.Organization()

        helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            group_id=org["name"],
        )

        send_confirmation_email.assert_called_once
        eq(send_confirmation_email.call_args[0][0].object_type, 'organization')
        eq(send_confirmation_email.call_args[0][0].object_id, org['id'])
        eq(send_confirmation_email.call_args[0][0].email, 'bob@example.com')

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_skip_verification(self, send_confirmation_email):
        dataset = factories.Dataset()

        subscription = helpers.call_action(
            "subscribe_signup",
            {},
            email='bob@example.com',
            dataset_id=dataset["id"],
            skip_verification=True,
        )

        assert not send_confirmation_email.called
        eq(subscription['object_type'], 'dataset')
        eq(subscription['object_id'], dataset['id'])
        eq(subscription['email'], 'bob@example.com')
        eq(subscription['verified'], True)

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_dataset_doesnt_exist(self, send_confirmation_email):
        with assert_raises(ValidationError) as cm:
            helpers.call_action(
                "subscribe_signup",
                {},
                email='bob@example.com',
                dataset_id='doesnt-exist',
            )
        assert_in("dataset_id': [u'Not found",
                  str(cm.exception.error_dict))

        assert not send_confirmation_email.called

    @mock.patch('ckanext.subscribe.email_verification.send_confirmation_email')
    def test_group_doesnt_exist(self, send_confirmation_email):
        with assert_raises(ValidationError) as cm:
            helpers.call_action(
                "subscribe_signup",
                {},
                email='bob@example.com',
                group_id='doesnt-exist',
            )
        assert_in("group_id': [u'That group name or ID does not exist",
                  str(cm.exception.error_dict))

        assert not send_confirmation_email.called
