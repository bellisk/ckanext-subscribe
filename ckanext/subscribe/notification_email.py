from ckan import plugins as p
from ckan import model

from ckanext.subscribe.email_auth import get_footer_contents

config = p.toolkit.config


def get_notification_email_contents(subscription):
    email_vars = get_notification_email_vars(subscription)
    plain_text_footer, html_footer = \
        get_footer_contents(code=None, subscription=subscription, email=None)
    email_vars['plain_text_footer'] = plain_text_footer
    email_vars['html_footer'] = html_footer

    subject = 'Confirm {site_title} subscription'.format(**email_vars)
    # Make sure subject is only one line
    subject = subject.split('\n')[0]

    html_body = '''
<p>{site_title} subscription requested<br/>
    {object_type}: "{object_title}" ({object_name})</p>

<p>To confirm this email subscription, click this link:<br/>
<a href="{verification_link}">{verification_link}</a></p>

--
<p style="font-size:10px;line-height:200%;text-align:center;color:#9EA3A8=
;padding-top:0px">
You can <a href="{unsubscribe_link}">unsubscribe</a> from notifications emails for {object_type}: "{object_title}".
</p>
<p style="font-size:10px;line-height:200%;text-align:center;color:#9EA3A8=
;padding-top:0px">
Or unsubscribe from <strong>all</strong> emails, please update your <a href="{manage_link}">settings</a>.
</p>
'''.format(**email_vars)
    plain_text_body = '''
{site_title} subscription requested:
{object_type}: {object_title} ({object_name})

To confirm this email subscription, click this link:
{verification_link}

--
You can unsubscribe from notifications emails for {object_type}: "{object_title}" going to {unsubscribe_link}.
Or unsubscribe from *all* emails by updating your settings at {manage_link}.
'''.format(**email_vars)
    return subject, plain_text_body, html_body


def get_notification_email_vars(subscription):
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
    unsubscribe_link = p.toolkit.url_for(
        controller='ckanext.subscribe.controller:SubscribeController',
        action='unsubscribe',
        object_id=subscription_object.id,
        qualified=True)
    extra_vars = dict(
        site_title=config.get('ckan.site_title'),
        site_url=config.get('ckan.site_url'),
        object_type=subscription.object_type,
        object_title=subscription_object.title or subscription_object.name,
        object_name=subscription_object.name,
        object_link=object_link,
        unsubscribe_link=unsubscribe_link,
        email=subscription.email,
        manage_link=manage_link,
    )
    return extra_vars
