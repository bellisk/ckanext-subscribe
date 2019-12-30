# encoding: utf-8

import datetime
import random
import string
from six import text_type

import ckan.plugins as p
from ckan import model
from ckanext.subscribe import mailer

config = p.toolkit.config

CODE_EXPIRY = datetime.timedelta(hours=8)


def send_request_email(subscription):
    subject, plain_text_body, html_body = \
        get_verification_email_contents(subscription)
    mailer.mail_recipient(recipient_name=subscription.email,
                          recipient_email=subscription.email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_verification_email_contents(subscription):
    email_vars = get_verification_email_vars(subscription)

    subject = 'Confirm your request for {site_title} subscription'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>{site_title} subscription requested<br/>
    {object_type}: "{object_title}" ({object_name})</p>

<p>To confirm this email subscription, click this link:<br/>
<a href="{verification_link}">{verification_link}</a></p>
'''.format(**email_vars)
    plain_text_body = '''
{site_title} subscription requested:
{object_type}: {object_title} ({object_name})

To confirm this email subscription, click this link:
{verification_link}
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def get_verification_email_vars(subscription):
    verification_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='verify_subscription',
        code=subscription.verification_code,
        qualified=True)
    manage_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='manage',
        qualified=True)
    if subscription.object_type == 'dataset':
        subscription_object = model.Package.get(subscription.object_id)
    else:
        subscription_object = model.Group.get(subscription.object_id)
    object_link = p.toolkit.url_for(
        controller='package' if subscription.object_type == 'dataset'
        else subscription.object_type,
        action='read',
        id=subscription.object_id,  # prefer id because it is invariant
        qualified=True)
    extra_vars = dict(
        site_title=config.get('ckan.site_title'),
        site_url=config.get('ckan.site_url'),
        object_type=subscription.object_type,
        object_title=subscription_object.title or subscription_object.name,
        object_name=subscription_object.name,
        object_link=object_link,
        verification_link=verification_link,
        email=subscription.email,
        manage_link=manage_link,
    )
    return extra_vars


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
