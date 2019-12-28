# encoding: utf-8

'''
"Email login" is a casual way to login to ckanext-subscribe. It is for changing
your subscription options. Rather than using a password, the user clicks on a
link containing a code in an email, thus proving they have access to the email
address. It's designed to be low fuss for occasionaly use.

The security is comparable to passwords, as they tend to fall back to emailed
links anyway. The links time-out so you don't have live links kicking around
your inbox for all time. Still, people do forward emails. And there is no
'log-out' button for people on shared computers. But arguably there's not a lot
of harm that an attacker could do, messing with your subscriptions.

This login is separate to CKAN's normal login, which uses a password.
'''

import datetime
import random
import string
from six import text_type

import ckan.plugins as p
from ckan import model
from ckan.common import session
from ckanext.subscribe import mailer
from ckanext.subscribe.model import LoginCode

log = __import__('logging').getLogger(__name__)
config = p.toolkit.config

CODE_EXPIRY = datetime.timedelta(days=7)
SESSION_LENGTH = datetime.timedelta(days=1)
EMAIL_SESSION_KEY = 'ckanext-subscribe-email'
EXPIRY_SESSION_KEY = 'ckanext-subscribe-expiry'


def send_login_email(email, code):
    subject, plain_text_body, html_body = \
        get_login_email_contents(email, code)
    mailer.mail_recipient(recipient_name=email,
                          recipient_email=email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_manage_email_contents(code, subscription=None, email=None):
    email_vars = get_email_vars(subscription=subscription, code=code)

    subject = 'Manage {site_title} subscription'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>{site_title} subscription options<br/>

<p>To manage subscriptions for {email}, click this link:<br/>
<a href="{manage_link}">{manage_link}</a></p>

--
<p style="font-size:10px;line-height:200%;text-align:center;color:#9EA3A8=
;padding-top:0px">
You can <a href="{unsubscribe_link}">unsubscribe</a> from notifications emails for {object_type}: "{object_title}".
</p>
<p style="font-size:10px;line-height:200%;text-align:center;color:#9EA3A8=
;padding-top:0px">
<a href="{manage_link}">Manage settings</a>.
</p>
'''.format(**email_vars)
    plain_text_body = '''
{site_title} subscription requested:

<p>To manage subscriptions for {email}, click this link:<br/>
{manage_link}

--
You can unsubscribe from notifications emails for {object_type}: "{object_title}" by going to {unsubscribe_link}.
Manage your settings at {manage_link}.
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def get_footer_contents(code, subscription=None, email=None):
    email_vars = get_email_vars(code, subscription=None, email=None)

    html_lines = []
    if subscription:
        html_lines.append(
            'You can <a href="{unsubscribe_link}">unsubscribe</a> from '
            'notifications emails for {object_type}: "{object_title}".'
        )
    html_lines.append('<a href="{manage_link}">Manage settings</a>')
    html_footer = '\n'.join(
        '<p style="font-size:10px;line-height:200%;text-align:center;'
        'color:#9EA3A8=;padding-top:0px">{msg}</p>'.format(line)
        for line in html_lines).format(**email_vars)

    plain_text_footer = '''
You can unsubscribe from notifications emails for {object_type}: "{object_title}" by going to {unsubscribe_link}.
Manage your settings at {manage_link}.
'''.format(**email_vars)
    return plain_text_footer, html_footer


def get_email_vars(code, subscription=None, email=None):
    assert subscription or email
    manage_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='manage',
        code=code,
        qualified=True)
    extra_vars = dict(
        site_title=config.get('ckan.site_title'),
        site_url=config.get('ckan.site_url'),
        email=email or subscription.email,
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
        extra_vars.update(
            object_type=subscription.object_type,
            object_title=subscription_object.title or subscription_object.name,
            object_name=subscription_object.name,
            object_link=object_link,
        )

    return extra_vars


def create_code(email):
    if p.toolkit.check_ckan_version(max_version='2.8.99'):
        model.repo.new_revision()
    code = text_type(make_code())
    model.LoginCode(
        code=code,
        expires=datetime.datetime.now() + CODE_EXPIRY,
    )
    model.repo.commit_and_remove()
    return code


def make_code():
    # random.SystemRandom() is documented as suitable for cryptographic use
    return ''.join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(32))


def get_session_email():
    if not session.get(EXPIRY_SESSION_KEY):
        return
    if datetime.datetime.now() > session.get(EXPIRY_SESSION_KEY):
        log.debug('Session expired')
        session.pop(EMAIL_SESSION_KEY)
        return
    return session.get(EMAIL_SESSION_KEY)


def login_with_code(code):
    # check the code is valid
    try:
        login_code = LoginCode.validate_code(code)
    except ValueError:
        raise
    # do the login
    login(login_code.email)

