# encoding: utf-8

import mock
import datetime

from nose.tools import assert_equal, assert_in

from ckan.tests.helpers import FunctionalTestBase, reset_db, submit_and_follow
from ckan.tests.factories import Dataset, Group, Organization

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.tests.factories import (
    Subscription,
    SubscriptionLowLevel,
)
from ckanext.subscribe import email_auth

eq = assert_equal


class TestSignupSubmit(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestSignupSubmit, cls).setup_class()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_dataset_ok(self, mock_mailer):
        dataset = Dataset()
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'dataset': dataset['id']},
            status=302)
        assert mock_mailer.called
        assert_equal(response.location,
                     'http://test.ckan.net/dataset/{}?__no_cache__=True'
                     .format(dataset['name']))

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_group_ok(self, mock_mailer):
        group = Group()
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': group['id']},
            status=302)
        assert mock_mailer.called
        assert_equal(response.location,
                     'http://test.ckan.net/group/{}?__no_cache__=True'
                     .format(group['name']))

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_org_ok(self, mock_mailer):
        org = Organization()
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': org['id']},
            status=302)
        assert mock_mailer.called
        assert_equal(response.location,
                     'http://test.ckan.net/organization/{}?__no_cache__=True'
                     .format(org['name']))

    def test_get_not_post(self):
        response = self._get_test_app().get('/subscribe/signup', status=400)
        response.mustcontain(u'No email address supplied')

    def test_object_not_specified(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com'},  # no dataset or group
            status=302).follow()
        response.mustcontain(u'Error subscribing: Must specify one of: '
                             '&#34;dataset_id&#34;')

    def test_dataset_missing(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'dataset': 'unknown'},
            ).follow(status=404)
        response.mustcontain(u'Dataset not found')

    def test_group_missing(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': 'unknown'},
            ).follow(status=404)
        response.mustcontain(u'Group not found')

    def test_empty_email(self):
        dataset = Dataset()
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': '', 'dataset': dataset['id']},
            status=400)
        response.mustcontain(u'No email address supplied')

    def test_bad_email(self):
        dataset = Dataset()
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'invalid email', 'dataset': dataset['id']},
            status=400)
        response.mustcontain(u'Email supplied is invalid')


class TestVerifySubscription(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestVerifySubscription, cls).setup_class()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_verify_dataset_ok(self, mock_mailer):
        dataset = Dataset()
        SubscriptionLowLevel(
            object_id=dataset['id'],
            object_type='dataset',
            email='bob@example.com',
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code='verify_code',
            verification_code_expires=datetime.datetime.now() +
            datetime.timedelta(hours=1)
        )

        response = self._get_test_app().post(
            '/subscribe/verify',
            params={'code': 'verify_code'},
            status=302)
        assert mock_mailer.called
        assert response.location.startswith(
            'http://test.ckan.net/subscribe/manage?code=')

    def test_wrong_code(self):
        response = self._get_test_app().post(
            '/subscribe/verify',
            params={'code': 'unknown_code'},
            status=302)
        eq(response.location, 'http://test.ckan.net/?__no_cache__=True')


class TestManage(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestManage, cls).setup_class()
        subscribe_model.setup()

    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/manage',
            params={'code': code},
            status=200)

        assert_in(dataset['title'], response.body.decode('utf8'))

    def test_no_code(self):
        response = self._get_test_app().get(
            '/subscribe/manage',
            params={'code': ''},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        response = self._get_test_app().get(
            '/subscribe/manage',
            params={'code': 'bad-code'},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')


class TestUpdate(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestUpdate, cls).setup_class()
        subscribe_model.setup()

    def test_submit(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().post(
            '/subscribe/update',
            params={'code': code, 'id': subscription['id'],
                    'frequency': 'daily'},
            status=302)

        assert response.location.startswith(
            'http://test.ckan.net/subscribe/manage?code=')
        response = response.follow()
        assert_in('<option value="DAILY" selected>',
                  response.body.decode('utf8'))

    def test_form_submit(self):
        Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/manage',
            params={'code': code},
            status=200)
        form = response.forms["frequency-form"]
        form["frequency"] = u"IMMEDIATE"
        response = submit_and_follow(self._get_test_app(), form, {}, "save")

        assert_in('<option value="IMMEDIATE" selected>',
                  response.body.decode('utf8'))

    def test_another_code(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code('someone_else@example.com')

        response = self._get_test_app().post(
            '/subscribe/update',
            params={'code': code, 'id': subscription['id'],
                    'frequency': 'daily'},
            status=302)
        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')


class TestUnsubscribe(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestUnsubscribe, cls).setup_class()
        subscribe_model.setup()

    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': dataset['id']},
            status=302)

        assert_equal(response.location,
                     'http://test.ckan.net/dataset/{}?__no_cache__=True'
                     .format(dataset['name']))

    def test_group(self):
        group = Group()
        Subscription(
            group_id=group['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'group': group['id']},
            status=302)

        assert_equal(response.location,
                     'http://test.ckan.net/group/{}?__no_cache__=True'
                     .format(group['name']))

    def test_org(self):
        org = Organization()
        Subscription(
            organization_id=org['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'organization': org['id']},
            status=302)

        assert_equal(response.location,
                     'http://test.ckan.net/organization/{}?__no_cache__=True'
                     .format(org['name']))

    def test_no_code(self):
        dataset = Dataset()
        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': '', 'dataset': dataset['id']},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        dataset = Dataset()
        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': 'bad-code', 'dataset': dataset['id']},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_no_subscription(self):
        dataset = Dataset()
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': dataset['id']},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/dataset/{}'.format(dataset['name']))
        response = response.follow()
        assert_in(
            'Error unsubscribing: That user is not subscribed to that object',
            response.body.decode('utf8'))

    def test_no_object(self):
        code = email_auth.create_code('bob@example.com')
        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': ''},
            status=302)

        eq(response.location, 'http://test.ckan.net/?__no_cache__=True')


class TestUnsubscribeAll(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestUnsubscribeAll, cls).setup_class()
        subscribe_model.setup()

    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe-all',
            params={'code': code},
            status=302)

        assert_equal(response.location,
                     'http://test.ckan.net/?__no_cache__=True')
        response = response.follow()
        assert_in('You are no longer subscribed to notifications from CKAN',
                  response.body.decode('utf8'))

    def test_no_code(self):
        response = self._get_test_app().get(
            '/subscribe/unsubscribe-all',
            params={'code': ''},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        response = self._get_test_app().get(
            '/subscribe/unsubscribe-all',
            params={'code': 'bad-code'},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_no_subscription(self):
        Dataset()
        code = email_auth.create_code('bob@example.com')

        response = self._get_test_app().get(
            '/subscribe/unsubscribe-all',
            params={'code': code},
            status=302)

        assert response.location.startswith(
           'http://test.ckan.net/')
        response = response.follow()
        assert_in(
            'Error unsubscribing: That user has no subscriptions',
            response.body.decode('utf8'))

    def test_no_object(self):
        code = email_auth.create_code('bob@example.com')
        response = self._get_test_app().get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': ''},
            status=302)

        eq(response.location, 'http://test.ckan.net/?__no_cache__=True')


class TestRequestManageCode(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        reset_db()
        super(TestRequestManageCode, cls).setup_class()
        subscribe_model.setup()

    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_basic(self, mail_recipient):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        response = self._get_test_app().get('/subscribe/request_manage_code')
        form = response.forms["request-manage-code-form"]
        form["email"] = u"bob@example.com"

        response = submit_and_follow(self._get_test_app(), form, {}, "save")

        mail_recipient.assert_called_once()
        assert_equal(response.request.path, '/')

    def test_no_email(self):
        self._get_test_app().post(
            '/subscribe/request_manage_code',
            params={'email': ''},
            status=200)
        # user is simply asked for the email

    def test_malformed_email(self):
        response = self._get_test_app().post(
            '/subscribe/request_manage_code',
            params={'email': 'malformed-email'},
            status=200)

        assert_in('Email malformed-email is not a valid format',
                  response.body.decode('utf8'))

    def test_unknown_email(self):
        response = self._get_test_app().post(
            '/subscribe/request_manage_code',
            params={'email': 'unknown@example.com'},
            status=200)

        assert_in('That email address does not have any subscriptions',
                  response.body.decode('utf8'))
