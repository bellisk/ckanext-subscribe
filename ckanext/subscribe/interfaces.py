from ckan.plugins.interfaces import Interface

from ckanext.subscribe.utils import get_footer_contents as \
    subscribe_get_footer_contents
from ckanext.subscribe.utils import get_email_vars as \
    subscribe_get_email_vars
from ckanext.subscribe.utils import get_manage_email_contents as \
    subscribe_get_manage_email_contents
from ckanext.subscribe.utils import \
    get_subscription_confirmation_email_contents \
    as subscribe_get_subscription_confirmation_email_contents
from ckanext.subscribe.utils import get_notification_email_contents as\
    subscribe_get_notification_email_contents
from ckanext.subscribe.utils import get_verification_email_contents as\
    subscribe_get_verification_email_contents


class ISubscribe(Interface):

    def get_footer_contents(self, email_vars, subscription=None,
                            plain_text_footer=None, html_footer=None):
        return subscribe_get_footer_contents(email_vars, subscription)

    def get_email_vars(self, code, subscription=None, email=None,
                       email_vars=None):
        return subscribe_get_email_vars(code, subscription, email)

    def get_manage_email_contents(self, email_vars, subject=None,
                                  plain_text_body=None, html_body=None):
        return subscribe_get_manage_email_contents(email_vars)

    def get_subscription_confirmation_email_contents(self, email_vars,
                                                     subject=None,
                                                     plain_text_body=None,
                                                     html_body=None):
        return subscribe_get_subscription_confirmation_email_contents(
            email_vars)

    def get_notification_email_contents(self, email_vars, subject=None,
                                        plain_text_body=None, html_body=None):
        return subscribe_get_notification_email_contents(email_vars)

    def get_verification_email_contents(self, subscription, subject=None,
                                        plain_text_body=None, html_body=None):
        return subscribe_get_verification_email_contents(subscription)
