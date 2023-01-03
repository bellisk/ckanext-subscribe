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
from ckanext.subscribe.utils import \
    filter_activities as subscribe_filter_activities


class ISubscribe(Interface):

    def get_footer_contents(self, email_vars, subscription=None,
                            plain_text_footer=None, html_footer=None):
        """Create a plain-text footer and html footer for an email.

        :param email_vars: Dict of strings to substitute into the text
        :type email_vars: dict
        :param subscription: Subscription object
        :type subscription: object
        :param plain_text_footer: Plain-text email footer, passed in here so
                                  that plugins can build on the results of
                                  other plugins implementing this interface
                                  Can contain <a> tags.
        :type plain_text_footer: string
        :param html_footer: HTML email footer, passed in here so
                                 that plugins can build on the results of
                                 other plugins implementing this interface
        :type html_footer: string
        :return: The plain-text footer and html footer
        :rtype: (string, string)
        """
        return subscribe_get_footer_contents(email_vars, subscription)

    def get_email_vars(self, code, subscription=None, email=None,
                       email_vars=None):
        """Get a dictionary of strings that can be substituted into email or
        footer text.

        :param code: Verification or authentication code
        :type code: string
        :param subscription: Subscription object
        :type subscription: object
        :param email: Address the email will be sent to
        :type email: string
        :param email_vars: Dictionary of email vars, passed in here so
                           that plugins can build on the results of
                           other plugins implementing this interface.
        :type email_vars: dict
        :return: The email_vars
        :rtype: dict
        """
        return subscribe_get_email_vars(code, subscription, email)

    def get_manage_email_contents(self, email_vars, subject=None,
                                  plain_text_body=None, html_body=None):
        """Get the plain-text body and html body of an email that links to the
        page for managing one email address's subscriptions.

        :param email_vars: Dict of strings to substitute into the text
        :type email_vars: dict
        :param subject: Subject line of the email
        :type subject: string
        :param plain_text_body: Plain-text body of the email, passed in here so
                                that plugins can build on the results of
                                other plugins implementing this interface.
        :type plain_text_body: string
        :param html_body: HTML body of the email, passed in here so
                          that plugins can build on the results of
                          other plugins implementing this interface.
        :type html_body: string
        :return: The plain-text body and html body
        :rtype: (string, string)
        """
        return subscribe_get_manage_email_contents(email_vars)

    def get_subscription_confirmation_email_contents(self, email_vars,
                                                     subject=None,
                                                     plain_text_body=None,
                                                     html_body=None):
        """Get the plain-text body and html body of an email confirming that
        a subscription has been created.

        :param email_vars: Dict of strings to substitute into the text
        :type email_vars: dict
        :param subject: Subject line of the email
        :type subject: string
        :param plain_text_body: Plain-text body of the email, passed in here so
                                that plugins can build on the results of
                                other plugins implementing this interface.
        :type plain_text_body: string
        :param html_body: HTML body of the email, passed in here so
                          that plugins can build on the results of
                          other plugins implementing this interface.
        :type html_body: string
        :return: The plain-text body and html body
        :rtype: (string, string)
        """
        return subscribe_get_subscription_confirmation_email_contents(
            email_vars)

    def get_notification_email_contents(self, email_vars, subject=None,
                                        plain_text_body=None, html_body=None):
        """Get the plain-text body and html body of an email with update
        notifications.

        :param email_vars: Dict of strings to substitute into the text
        :type email_vars: dict
        :param subject: Subject line of the email
        :type subject: string
        :param plain_text_body: Plain-text body of the email, passed in here so
                                that plugins can build on the results of
                                other plugins implementing this interface.
        :type plain_text_body: string
        :param html_body: HTML body of the email, passed in here so
                          that plugins can build on the results of
                          other plugins implementing this interface.
        :type html_body: string
        :return: The plain-text body and html body
        :rtype: (string, string)
        """
        return subscribe_get_notification_email_contents(email_vars)

    def get_verification_email_contents(self, email_vars, subject=None,
                                        plain_text_body=None, html_body=None):
        """Get the plain-text body and html body of an email with a link to
        verify (confirm) that a subscription should be created.

        :param email_vars: Dict of strings to substitute into the text
        :type email_vars: dict
        :param subject: Subject line of the email
        :type subject: string
        :param plain_text_body: Plain-text body of the email, passed in here so
                                that plugins can build on the results of
                                other plugins implementing this interface.
        :type plain_text_body: string
        :param html_body: HTML body of the email, passed in here so
                          that plugins can build on the results of
                          other plugins implementing this interface.
        :type html_body: string
        :return: The plain-text body and html body
        :rtype: (string, string)
        """
        return subscribe_get_verification_email_contents(email_vars)

    def get_activities(self, include_activity_from,
                       objects_subscribed_to_keys):
        """Get the activities for object subscription keys and date.
        :param include_activity_from: timestamps for actvity selection
        :type include_activity_from: timestamp
        :param objects_subscribed_to_keys: Subject line of the email
        :type objects_subscribed_to_keys: list of strings
        :return: activities from the database
        :rtype: list of objects
        """
        return subscribe_filter_activities(include_activity_from, objects_subscribed_to_keys)
