# encoding: utf-8

from nose.tools import assert_equal

from ckan import plugins as p
from ckan import model
from ckan.tests import factories as ckan_factories
from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.email_verification import (
    get_verification_email_vars,
    get_verification_email_contents
)
from ckanext.subscribe.tests import factories

config = p.toolkit.config


class TestEmailVerification(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_get_verification_email_vars(self):
        dataset = ckan_factories.Dataset()
        subscription = factories.Subscription(
            dataset_id=dataset['id'], return_object=True)
        subscription.verification_code = 'testcode'

        email_vars = get_verification_email_vars(subscription)

        assert_equal(email_vars['site_title'], config['ckan.site_title'])
        assert_equal(email_vars['site_url'],
                     'http://test.ckan.net')
        assert_equal(email_vars['object_title'], 'Test Dataset')
        assert_equal(email_vars['object_type'], 'dataset')
        assert_equal(email_vars['email'], 'bob@example.com')
        assert_equal(email_vars['verification_link'],
                     'http://test.ckan.net/packages?code=testcode')
        assert_equal(email_vars['object_link'],
                     'http://test.ckan.net/dataset/{}'.format(dataset['id']))

    def test_get_verification_email_contents(self):
        dataset = ckan_factories.Dataset()
        subscription = factories.Subscription(
            dataset_id=dataset['id'], return_object=True)
        subscription.verification_code = 'testcode'

        subject, body = get_verification_email_contents(subscription)

        assert_equal(subject, 'Confirm CKAN subscription')
        assert body.strip().startswith('CKAN subscription requested:')