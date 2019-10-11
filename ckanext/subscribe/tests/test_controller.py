from ckan.tests.helpers import FunctionalTestBase


class TestSignon(FunctionalTestBase):
    _load_plugins = ['subscribe']

    def test_get(self):
        self._get_test_app().get('/subscribe/signup', status=400)

    def test_no_email(self):
        response = self._get_test_app().post('/subscribe/signup', status=400)
        response.mustcontain(u'No email address supplied')

    def test_bad_email(self):
        response = self._get_test_app().post(
            '/subscribe/signup',
            params={'email': 'invalid email'},
            status=400)
        response.mustcontain(u'Email supplied is invalid')
