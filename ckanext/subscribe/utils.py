# encoding: utf-8
from jinja2 import Template

import ckan.plugins as p
from ckan import model
from ckan.model import Activity

config = p.toolkit.config


def get_footer_contents(email_vars, subscription=None):
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
        qualified=True
    )
    manage_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='manage',
        code=code,
        qualified=True
    )
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


def get_manage_email_contents(email_vars):
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


def get_subscription_confirmation_email_contents(email_vars):
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


def get_notification_email_contents(email_vars):
    subject = '{site_title} notification'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = Template('''
<p>Changes have occurred in relation to your subscription(s)</p>

{% for notification in notifications %}

  <h3><a href="{{ notification.object_link }}">"{{ notification.object_title }}" ({{ notification.object_name }})</a>:</h3>

  {% for activity in notification.activities %}
    <p>
      - {{ activity.timestamp.strftime('%Y-%m-%d %H:%M') }} -
      {{ activity.activity_type }}
      {% if notification.object_type != 'dataset' %}
        - {{ activity.dataset_link }}
      {% endif %}
    </p>
  {% endfor %}
{% endfor %}

--
{{ html_footer }}
''').render(**email_vars)
    plain_text_body = Template('''
Changes have occurred in relation to your subscription(s)

{% for notification in notifications %}
  "{{ notification.object_title }}" - {{ notification.object_link }}

  {% for activity in notification.activities %}
      - {{ activity.timestamp.strftime('%Y-%m-%d %H:%M') }} - {{ activity.activity_type }} {% if (
          notification.object_type != 'dataset') %} - {{ activity.dataset_href }} {% endif %}

  {% endfor %}
{% endfor %}

--
{{ plain_text_footer }}
''').render(**email_vars)
    return subject, plain_text_body, html_body


def get_verification_email_contents(email_vars):
    subject = 'Confirm your request for {site_title} subscription'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>{site_title} subscription requested<br/>
    {object_type}: "{object_title}" ({object_name})</p>

<p>To confirm this email subscription, click this link:<br/>
<a href="{verification_link}">{verification_link}</a></p>

--
{html_footer}
'''.format(**email_vars)
    plain_text_body = '''
{site_title} subscription requested:
{object_type}: {object_title} ({object_name})

To confirm this email subscription, click this link:
{verification_link}

--
{plain_text_footer}
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def filter_activities(include_activity_from, objects_subscribed_to_keys):
    activities = model.Session.query(Activity)\
                              .filter(Activity.timestamp > include_activity_from) \
                              .filter(Activity.object_id.in_(objects_subscribed_to_keys)) \
                              .all()
    return activities
