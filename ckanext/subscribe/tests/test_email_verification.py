# encoding: utf-8

from nose.tools import assert_equal

from ckan import plugins as p
from ckan.tests import factories as ckan_factories
from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.email_verification import (
    get_verification_email_vars,
)
from ckanext.subscribe.tests import factories
from ckanext.subscribe.utils import (
    get_footer_contents,
    get_verification_email_contents
)

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
                     'http://test.ckan.net/subscribe/verify?code=testcode')
        assert_equal(email_vars['object_link'],
                     'http://test.ckan.net/dataset/{}'.format(dataset['id']))

    def test_get_verification_email_contents(self):
        dataset = ckan_factories.Dataset()
        subscription = factories.Subscription(
            dataset_id=dataset['id'], return_object=True)
        subscription.verification_code = 'testcode'

        email_vars = get_verification_email_vars(subscription)
        plain_text_footer, html_footer = get_footer_contents(email_vars)
        email_vars['plain_text_footer'] = plain_text_footer
        email_vars['html_footer'] = html_footer
        subject, body_plain_text, body_html = \
            get_verification_email_contents(email_vars)

        assert_equal(subject, 'Confirm your request for CKAN subscription')
        assert body_plain_text.strip().startswith(
            'CKAN subscription requested'), body_plain_text.strip()
        assert body_html.strip().startswith(
            '<p>CKAN subscription requested'), body_html.strip()
