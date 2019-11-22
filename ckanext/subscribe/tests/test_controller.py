# encoding: utf-8

from ckan.tests.helpers import FunctionalTestBase


class TestSignupSubmit(FunctionalTestBase):
    _load_plugins = ['subscribe']

    def test_signup_ok(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'bob@example.com'},
            status=302)
        assert response.location.endswith('/subscribe/manage')

    def test_get_not_post(self):
        response = self._get_test_app().get('/subscribe/signup', status=400)
        response.mustcontain(u'No email address supplied')

    def test_empty_email(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': ''},
            status=400)
        response.mustcontain(u'No email address supplied')

    def test_bad_email(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'invalid email'},
            status=400)
        response.mustcontain(u'Email supplied is invalid')
