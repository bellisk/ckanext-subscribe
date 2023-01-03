# encoding: utf-8

import datetime
import random
import string
from six import text_type

import ckan.plugins as p
from ckan import model
from ckanext.subscribe import mailer
from ckanext.subscribe.interfaces import ISubscribe

config = p.toolkit.config

CODE_EXPIRY = datetime.timedelta(hours=8)


def send_request_email(subscription):
    email_vars = get_verification_email_vars(subscription)

    plain_text_footer = html_footer = ""
    for subscribe in p.PluginImplementations(ISubscribe):
        # We pass in subscription=None here because there is no active
        # subscription yet, so we don't want to include an unsubscribe link.
        plain_text_footer, html_footer = \
            subscribe.get_footer_contents(email_vars, subscription=None,
                                          plain_text_footer=plain_text_footer,
                                          html_footer=html_footer)

    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = plain_text_body = html_body = ''
    for subscribe in p.PluginImplementations(ISubscribe):
        subject, plain_text_body, html_body = \
            subscribe.get_verification_email_contents(email_vars, subject,
                                                      plain_text_body,
                                                      html_body)

    mailer.mail_recipient(recipient_name=subscription.email,
                          recipient_email=subscription.email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_verification_email_vars(subscription):
    email_vars = {}
    for subscribe in p.PluginImplementations(ISubscribe):
        email_vars = subscribe.get_email_vars(
            code=subscription.verification_code, subscription=subscription,
            email_vars=email_vars)

    verification_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='verify_subscription',
        code=subscription.verification_code,
        qualified=True)
    manage_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='manage',
        qualified=True)
    email_vars.update(
        verification_link=verification_link,
        manage_link=manage_link,
    )
    return email_vars


def create_code(subscription):
    subscription.verification_code = text_type(make_code())
    subscription.verification_code_expires = \
        datetime.datetime.now() + CODE_EXPIRY
    model.repo.commit_and_remove()


def make_code():
    # random.SystemRandom() is documented as suitable for cryptographic use
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(32))
