from ckan.plugins.interfaces import Interface

from ckanext.subscribe.utils import get_footer_contents as subscribe_get_footer_contents
from ckanext.subscribe.utils import get_email_vars as subscribe_get_email_vars
from ckanext.subscribe.utils import get_manage_email_contents as subscribe_get_manage_email_contents
from ckanext.subscribe.utils import get_subscription_confirmation_email_contents as subscribe_get_subscription_confirmation_email_contents


class ISubscribe(Interface):

    def get_footer_contents(self, plain_text_footer, html_footer, code, subscription=None, email=None):
        return subscribe_get_footer_contents(code, subscription, email)

    def get_email_vars(self, email_vars, code, subscription=None, email=None):
        return subscribe_get_email_vars(code, subscription, email)

    def get_manage_email_contents(self, subject, plain_text_body, html_body, code, subscription=None, email=None):
        return subscribe_get_manage_email_contents(code, subscription, email)

    def get_subscription_confirmation_email_contents(self, subject, plain_text_body, html_body, code, subscription):
        return subscribe_get_subscription_confirmation_email_contents(code, subscription)

