# encoding: utf-8

'''
"Email auth" is a way to authenticate to access certain pages to
ckanext-subscribe. It is used for changing your subscription options. Rather
than using a password, the user clicks on a link containing a code in an email,
thus proving they have access to the email address. It's designed to be low
fuss for occasional use.

The security is comparable to passwords, as they tend to fall back to emailed
links anyway. The links time-out so you don't have live links kicking around
your inbox for all time. Still, people do forward emails. The code just exists
in the URL - it is not saved in a cookie or session, so there's no 'log-out'
button. People on shared computers would find that others can find the page in
the history. But arguably there's not a lot of harm that an attacker could do,
messing with your subscriptions.

This login is separate to CKAN's normal login, which uses a password.
'''

import datetime
import random
import string
from six import text_type

import ckan.plugins as p
from ckan import model
from ckanext.subscribe import mailer
from ckanext.subscribe.interfaces import ISubscribe
from ckanext.subscribe.model import LoginCode

log = __import__('logging').getLogger(__name__)
config = p.toolkit.config

CODE_EXPIRY = datetime.timedelta(days=7)


def send_subscription_confirmation_email(code, subscription=None):
    email_vars = {}
    for subscribe in p.PluginImplementations(ISubscribe):
        email_vars = subscribe.get_email_vars(
            subscription=subscription, code=code, email_vars=email_vars)

    plain_text_footer = html_footer = ""
    for subscribe in p.PluginImplementations(ISubscribe):
        plain_text_footer, html_footer = \
            subscribe.get_footer_contents(email_vars, subscription=subscription,
                                          plain_text_footer=plain_text_footer,
                                          html_footer=html_footer)

    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = plain_text_body = html_body = ""
    for subscribe in p.PluginImplementations(ISubscribe):
        subject, plain_text_body, html_body = \
            subscribe.get_subscription_confirmation_email_contents(
                email_vars, subject=subject,
                plain_text_body=plain_text_body, html_body=html_body)

    mailer.mail_recipient(recipient_name=subscription.email,
                          recipient_email=subscription.email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def send_manage_email(code, subscription=None, email=None):
    email_vars = {}
    for subscribe in p.PluginImplementations(ISubscribe):
        email_vars = subscribe.get_email_vars(
            code=code, subscription=subscription, email=email,
            email_vars=email_vars)

    plain_text_footer = html_footer = ""
    for subscribe in p.PluginImplementations(ISubscribe):
        plain_text_footer, html_footer = \
            subscribe.get_footer_contents(email_vars, subscription=subscription,
                                          plain_text_footer=plain_text_footer,
                                          html_footer=html_footer)

    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = plain_text_body = html_body = ""
    for subscribe in p.PluginImplementations(ISubscribe):
        subject, plain_text_body, html_body = \
            subscribe.get_manage_email_contents(
                email_vars, subject=subject, plain_text_body=plain_text_body,
                html_body=html_body)

    mailer.mail_recipient(recipient_name=email,
                          recipient_email=email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def create_code(email):
    if p.toolkit.check_ckan_version(max_version='2.8.99'):
        model.repo.new_revision()
    code = text_type(make_code())
    model.Session.add(LoginCode(
        email=email,
        code=code,
        expires=datetime.datetime.now() + CODE_EXPIRY,
    ))
    model.repo.commit_and_remove()
    return code


def make_code():
    # random.SystemRandom() is documented as suitable for cryptographic use
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(32))


def authenticate_with_code(code):
    # check the code is valid
    try:
        login_code = LoginCode.validate_code(code)
    except ValueError:
        raise
    # do the login
    return login_code.email
