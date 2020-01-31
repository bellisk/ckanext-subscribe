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
from ckanext.subscribe.model import LoginCode

log = __import__('logging').getLogger(__name__)
config = p.toolkit.config

CODE_EXPIRY = datetime.timedelta(days=7)


def send_subscription_confirmation_email(code, subscription=None):
    subject, plain_text_body, html_body = \
        get_subscription_confirmation_email_contents(
            code=code, subscription=subscription)
    mailer.mail_recipient(recipient_name=subscription.email,
                          recipient_email=subscription.email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_subscription_confirmation_email_contents(code, subscription):
    email_vars = get_email_vars(subscription=subscription, code=code)
    plain_text_footer, html_footer = \
        get_footer_contents(code, subscription=subscription)
    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = '{site_title} subscription confirmed'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>You have subscribed to notifications about:<br/>
{object_type}: <a href="{object_link}">{object_title} ({object_name})</a></p>

<p>To manage subscriptions for {email}, click this link:<br/>
{manage_link}</p>

--
{html_footer}
'''.format(**email_vars)
    plain_text_body = '''
You have subscribed to notifications about:
{object_type}: {object_title} ({object_name})
{object_link}

To manage subscriptions for {email}, click this link:
{manage_link}

--
{plain_text_footer}
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def send_manage_email(code, subscription=None, email=None):
    subject, plain_text_body, html_body = \
        get_manage_email_contents(code, subscription=subscription, email=email)
    mailer.mail_recipient(recipient_name=email,
                          recipient_email=email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_manage_email_contents(code, subscription=None, email=None):
    email_vars = get_email_vars(code, subscription=subscription, email=email)
    plain_text_footer, html_footer = \
        get_footer_contents(code, subscription=subscription, email=email)
    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = 'Manage {site_title} subscription'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>{site_title} subscription options<br/>

<p>To manage subscriptions for {email}, click this link:<br/>
<a href="{manage_link}">{manage_link}</a></p>

--
{html_footer}
'''.format(**email_vars)
    plain_text_body = '''
{site_title} subscription requested:

<p>To manage subscriptions for {email}, click this link:<br/>
{manage_link}

--
{plain_text_footer}
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def get_footer_contents(code, subscription=None, email=None):
    email_vars = get_email_vars(code, subscription=subscription, email=email)

    html_lines = []
    if subscription:
        html_lines.append(
            'To stop receiving emails of this type: '
            '<a href="{unsubscribe_link}">'
            'unsubscribe from {object_type} "{object_title}"</a>'
        )
    else:
        html_lines.append(
            'To stop receiving all subscription emails from {site_title}: '
            '<a href="{unsubscribe_all_link}">'
            'unsubscribe all</a>'
        )
    html_lines.append('<a href="{manage_link}">Manage settings</a>')
    html_footer = '\n'.join(
        '<p style="font-size:10px;line-height:200%;text-align:center;'
        'color:#9EA3A8=;padding-top:0px">{line}</p>'.format(line=line)
        for line in html_lines).format(**email_vars)

    plain_text_footer = ''
    if subscription:
        plain_text_footer += '''
You can unsubscribe from notifications emails for {object_type}: "{object_title}" by going to {unsubscribe_link}.
'''.format(**email_vars)
    else:
        plain_text_footer += (
            'To stop receiving all subscription emails from {site_title}: '
            '<a href="{unsubscribe_all_link}">'
            'unsubscribe all</a>'
        ).format(**email_vars)
    plain_text_footer += '''
Manage your settings at {manage_link}.
'''.format(**email_vars)
    return plain_text_footer, html_footer


def get_email_vars(code, subscription=None, email=None):
    '''
    Get the variables to substitute into email templates.

    If you have a subscription object, not just an email address, then you get
    the object_* variables which allow you to link to the object subscribed to.

    :param code: the email auth code (required)
    :param subscription: subscription object (optional)
    :param email: email address of the user (supply a value if subscription is
        not available)
    '''
    assert code
    assert subscription or email
    unsubscribe_all_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='unsubscribe_all',
        code=code,
        qualified=True)
    manage_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='manage',
        code=code,
        qualified=True)
    extra_vars = dict(
        site_title=config.get('ckan.site_title'),
        site_url=config.get('ckan.site_url'),
        email=email or subscription.email,
        unsubscribe_all_link=unsubscribe_all_link,
        manage_link=manage_link,
    )

    if subscription:
        if subscription.object_type == 'dataset':
            subscription_object = model.Package.get(subscription.object_id)
        else:
            subscription_object = model.Group.get(subscription.object_id)
        object_link = p.toolkit.url_for(
            controller='package' if subscription.object_type == 'dataset'
            else subscription.object_type,
            action='read',
            id=subscription.object_id,
            qualified=True)
        unsubscribe_link = p.toolkit.url_for(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='unsubscribe',
            code=code,
            qualified=True,
            **{subscription.object_type: subscription.object_id}
            )
        extra_vars.update(
            object_type=subscription.object_type,
            object_title=subscription_object.title or subscription_object.name,
            object_name=subscription_object.name,
            object_link=object_link,
            unsubscribe_link=unsubscribe_link,
        )

    return extra_vars


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
