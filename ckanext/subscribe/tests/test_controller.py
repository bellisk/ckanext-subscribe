# encoding: utf-8

import mock

from nose.tools import assert_equal

from ckan.tests.helpers import FunctionalTestBase, reset_db
from ckan.tests.factories import Dataset, Group, Organization

from ckanext.subscribe import model as subscribe_model


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
                     .format(dataset['id']))

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
                     .format(group['id']))

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
                     .format(org['id']))

    def test_get_not_post(self):
        response = self._get_test_app().get('/subscribe/signup', status=400)
        response.mustcontain(u'No email address supplied')

    def test_object_not_specified(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com'},  # no dataset or group
            status=302).follow()
        response.mustcontain(u'Error subscribing: Must specify either '
                             '&#34;dataset_id&#34; or &#34;group_id&#34;')

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


class TestManage(object):
