# encoding: utf-8

import logging
import datetime

import ckan.plugins as p
from ckan.logic import validate  # put in toolkit?
from ckan.lib.mailer import MailerException

from ckanext.subscribe.model import Subscription, Frequency
from ckanext.subscribe import (
    schema,
    dictization,
    email_verification,
    email_auth,
    notification,
)

log = logging.getLogger(__name__)
_check_access = p.toolkit.check_access
NotFound = p.toolkit.ObjectNotFound


@validate(schema.subscribe_schema)
def subscribe_signup(context, data_dict):
    '''Signup to get notifications of email. Causes a email to be sent,
    containing a verification link.

    :param email: Email address to get notifications to
    :param dataset_id: Dataset name or id to get notifications about
        (specify only one of: dataset_id or group_id or organization_id)
    :param group_id: Group or organization name or id to get notifications
        about (specify only one of: dataset_id or group_id or organization_id)
    :param organization_id: Organization name or id to get notifications
        about (specify only one of: dataset_id or group_id or organization_id)
    :param frequency: Frequency of notifications to receive. One of:
        'immediate', 'daily', 'weekly' (optional, default=immediate)
    :param skip_verification: Doesn't send email - instead it marks the
        subscription as verified. Can be used by sysadmins only.
        (optional, default=False)

    :returns: the newly created subscription
    :rtype: dictionary

    '''
    model = context['model']

    _check_access(u'subscribe_signup', context, data_dict)

    data = {
        'email': data_dict['email'],
        'frequency': data_dict.get('frequency', Frequency.IMMEDIATE.value),
    }
    if data_dict.get('dataset_id'):
        data['object_type'] = 'dataset'
        dataset_obj = model.Package.get(data_dict['dataset_id'])
        data['object_id'] = dataset_obj.id
        data['object_name'] = dataset_obj.name
    else:
        group_obj = model.Group.get(data_dict.get('group_id') or
                                    data_dict.get('organization_id'))
        if group_obj.is_organization:
            data['object_type'] = 'organization'
        else:
            data['object_type'] = 'group'
        data['object_id'] = group_obj.id
        data['object_name'] = group_obj.name

    # must be unique combination of email/object_type/object_id
    existing = model.Session.query(Subscription) \
        .filter_by(email=data['email']) \
        .filter_by(object_type=data['object_type']) \
        .filter_by(object_id=data['object_id']) \
        .first()
    if existing:
        # reuse existing subscription
        subscription = existing
        subscription.frequency = data['frequency']
    else:
        # create subscription object
        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            rev = model.repo.new_revision()
            rev.author = context['user']
        subscription = dictization.subscription_save(data, context)
        model.repo.commit()

    # send 'confirm your request' email
    if data_dict['skip_verification']:
        subscription.verified = True
        model.repo.commit()
    else:
        email_verification.create_code(subscription)
        try:
            email_verification.send_request_email(subscription)
        except MailerException as exc:
            log.error('Could not email manage code: {}'.format(exc))
            raise

    subscription_dict = dictization.dictize_subscription(subscription, context)
    subscription_dict['object_name'] = data['object_name']
    return subscription_dict


def subscribe_verify(context, data_dict):
    '''Verify (confirm) a subscription

    :param code: Verification code, supplied in the email sent on sign-up

    :returns: the updated subscription
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    _check_access(u'subscribe_verify', context, data_dict)

    code = p.toolkit.get_or_bust(data_dict, 'code')
    subscription = model.Session.query(Subscription) \
        .filter_by(verification_code=code) \
        .first()
    if not subscription:
        raise p.toolkit.ValidationError(
            'That validation code is not recognized')
    if subscription.verification_code_expires < datetime.datetime.now():
        raise p.toolkit.ValidationError(
            'That validation code has expired')

    # Verify the subscription
    if p.toolkit.check_ckan_version(max_version='2.8.99'):
        rev = model.repo.new_revision()
        rev.author = user
    subscription.verified = True
    subscription.verification_code = None  # it can't be used again
    subscription.verification_code_expires = None
    if not context.get('defer_commit'):
        model.repo.commit()

    # Email the user confirmation and so they have a link to manage it
    manage_code = email_auth.create_code(subscription.email)
    email_auth.send_subscription_confirmation_email(
        manage_code, subscription=subscription)

    return dictization.dictize_subscription(subscription, context)


@validate(schema.update_schema)
def subscribe_update(context, data_dict):
    '''Update a subscription's configuration.

    :param id: Subscription id to update
    :param frequency: Frequency of notifications to receive. One of:
        'immediate', 'daily', 'weekly' (optional, default=unchanged)

    :returns: the updated subscription
    :rtype: dictionary

    '''
    model = context['model']

    _check_access(u'subscribe_update', context, data_dict)

    id_ = p.toolkit.get_or_bust(data_dict, 'id')
    subscription = model.Session.query(Subscription).get(id_)

    for key in ('frequency',):
        if not data_dict.get(key):
            continue
        setattr(subscription, key, data_dict[key])
    model.repo.commit()

    subscription_dict = dictization.dictize_subscription(subscription, context)
    return subscription_dict


def subscribe_list_subscriptions(context, data_dict):
    '''For a given email address, list the subscriptions

    :param email: email address of the user to get the subscriptions for

    :rtype: list of subscription dicts
    '''
    model = context['model']

    _check_access(u'subscribe_list_subscriptions', context, data_dict)
    email = p.toolkit.get_or_bust(data_dict, 'email')

    subscription_objs = \
        model.Session.query(Subscription, model.Package, model.Group) \
        .filter_by(email=email) \
        .outerjoin(model.Package, Subscription.object_id == model.Package.id) \
        .outerjoin(model.Group, Subscription.object_id == model.Group.id) \
        .all()
    subscriptions = []
    for subscription_obj, package, group in subscription_objs:
        subscription = \
            dictization.dictize_subscription(subscription_obj, context)
        if package:
            subscription['object_name'] = package.name
            subscription['object_title'] = package.title
            subscription['object_link'] = p.toolkit.url_for(
                controller='package', action='read', id=package.name)
        elif group and not group.is_organization:
            subscription['object_name'] = group.name
            subscription['object_title'] = group.title
            subscription['object_link'] = p.toolkit.url_for(
                controller='group', action='read', id=group.name)
        elif group and group.is_organization:
            subscription['object_name'] = group.name
            subscription['object_title'] = group.title
            subscription['object_link'] = p.toolkit.url_for(
                controller='organization', action='read', id=group.name)
        subscriptions.append(subscription)
    return subscriptions


@validate(schema.unsubscribe_schema)
def subscribe_unsubscribe(context, data_dict):
    '''Unsubscribe from notifications on a given object

    :param email: Email address to unsubscribe
    :param dataset_id: Dataset name or id to unsubscribe from
        (specify only one of: dataset_id or group_id or organization_id)
    :param group_id: Group or organization name or id to unsubscribe from
        about (specify only one of: dataset_id or group_id or organization_id)
    :param organization_id: Organization name or id to unsubscribe from
        about (specify only one of: dataset_id or group_id or organization_id)

    :returns: (object_name, object_type) where object_type is: dataset, group
        or organization
    :rtype: (str, str)

    '''
    model = context['model']

    _check_access(u'subscribe_unsubscribe', context, data_dict)

    data = {
        'email': p.toolkit.get_or_bust(data_dict, 'email'),
        'user': context['user']
    }
    if data_dict.get('dataset_id'):
        data['object_type'] = 'dataset'
        dataset_obj = model.Package.get(data_dict['dataset_id'])
        data['object_id'] = dataset_obj.id
        data['object_name'] = dataset_obj.name
    else:
        group_obj = model.Group.get(data_dict.get('group_id') or
                                    data_dict.get('organization_id'))
        if group_obj.is_organization:
            data['object_type'] = 'organization'
        else:
            data['object_type'] = 'group'
        data['object_id'] = group_obj.id
        data['object_name'] = group_obj.name

    subscription = model.Session.query(Subscription) \
        .filter_by(email=data['email']) \
        .filter_by(object_id=data['object_id']) \
        .first()
    if not subscription:
        raise p.toolkit.ObjectNotFound(
            'That user is not subscribed to that object')
    model.Session.delete(subscription)
    model.repo.commit()

    return data['object_name'], data['object_type']


@validate(schema.unsubscribe_all_schema)
def subscribe_unsubscribe_all(context, data_dict):
    '''Unsubscribe an email from all notifications

    :param email: Email address to unsubscribe

    :returns: None
    '''
    model = context['model']

    _check_access(u'subscribe_unsubscribe_all', context, data_dict)

    data = {
        'email': p.toolkit.get_or_bust(data_dict, 'email'),
        'user': context['user']
    }

    subscriptions = model.Session.query(Subscription) \
        .filter_by(email=data['email']) \
        .all()
    if not subscriptions:
        raise p.toolkit.ObjectNotFound(
            'That user has no subscriptions')
    for subscription in subscriptions:
        model.Session.delete(subscription)
    model.repo.commit()


@validate(schema.request_manage_code_schema)
def subscribe_request_manage_code(context, data_dict):
    '''Request a code for managing existing subscriptions. Causes a email to be
    sent, containing a manage link.

    :param email: Email address to get a code for

    :returns: null
    '''
    model = context['model']

    _check_access(u'subscribe_request_manage_code', context, data_dict)

    email = data_dict['email']

    # check they have a subscription
    subscription = model.Session.query(Subscription) \
        .filter_by(email=email) \
        .first()
    if not subscription:
        raise p.toolkit.ObjectNotFound(
            'That email address does not have any subscriptions')

    # create and send a code
    manage_code = email_auth.create_code(subscription.email)
    try:
        email_auth.send_manage_email(manage_code, email=email)
    except MailerException as exc:
        log.error('Could not email manage code: {}'.format(exc))
        raise

    return None


def subscribe_send_any_notifications(context, data_dict):
    '''Check for activity and for any subscribers, send emails with the
    notifications.
    '''
    notification.send_any_immediate_notifications()
    notification.send_weekly_notifications_if_its_time_to()
    notification.send_daily_notifications_if_its_time_to()
    return None
