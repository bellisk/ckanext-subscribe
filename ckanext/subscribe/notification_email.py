from jinja2 import Template

from ckan import plugins as p
from ckan import model

from ckanext.subscribe import mailer
from ckanext.subscribe.email_auth import get_footer_contents

config = p.toolkit.config


def send_notification_email(code, email, notifications):
    subject, plain_text_body, html_body = \
        get_notification_email_contents(code, email, notifications)
    mailer.mail_recipient(recipient_name=email,
                          recipient_email=email,
                          subject=subject,
                          body=plain_text_body,
                          body_html=html_body,
                          headers={})


def get_notification_email_contents(code, email, notifications):
    email_vars = get_notification_email_vars(email, notifications)
    plain_text_footer, html_footer = \
        get_footer_contents(code=code, email=email)
    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = '{site_title} notification'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = Template('''
<p>Changes have occurred in relation to your subscription(s)</p>

{% for notification in notifications %}

  <h3><a href="{{ notification.object_link }}">"{{ notification.object_title }}" ({{ notification.object_name }})</a>:</h3>

  {% for activity in notification.activities %}
    <p>
      * {{ activity.timestamp.strftime('%Y-%m-%d %H:%M') }} -
      {{ activity.activity_type }}
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
      * {{ activity.timestamp.strftime('%Y-%m-%d %H:%M') }} - {{ activity.activity_type }}
  {% endfor %}
{% endfor %}

--
{{ plain_text_footer }}
''').render(**email_vars)
    return subject, plain_text_body, html_body


def get_notification_email_vars(email, notifications):
    notifications_vars = []
    for notification in notifications:
        subscription = notification['subscription']
        activities = notification['activities']
        activities_vars = []
        for activity in activities:
            activities_vars.append(dict(
                activity_type=activity['activity_type'].replace('package', 'dataset'),
                timestamp=p.toolkit.h.date_str_to_datetime(activity['timestamp']),
            ))
        # get the package/group's name & title
        object_type_ = \
            subscription['object_type'].replace('dataset', 'package')
        try:
            # activity['data'] should have the package/group table
            obj = notification['activities'][0]['data'][object_type_]
            object_name = obj['name']
            object_title = obj['title']
        except KeyError:
            # activity['data'] has gone missing - resort to the db
            if subscription['object_type'] == 'dataset':
                obj = model.Package.get(subscription['object_id'])
            else:
                obj = model.Group.get(subscription['object_id'])
            object_name = obj.name
            object_title = obj.title
        object_link = p.toolkit.url_for(
            controller=object_type_,
            action='read',
            id=subscription['object_id'],  # prefer id because it is invariant
            qualified=True)
        notifications_vars.append(dict(
            activities=activities_vars,
            object_type=subscription['object_type'],
            object_title=object_title or object_name,
            object_name=object_name,
            object_link=object_link,
        ))

    extra_vars = dict(
        site_title=config.get('ckan.site_title'),
        site_url=config.get('ckan.site_url'),
        email=email,
        notifications=notifications_vars,
    )
    return extra_vars
