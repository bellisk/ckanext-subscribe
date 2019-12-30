# encoding: utf-8

import logging
import datetime

import ckan.plugins as p
from ckan.logic import validate  # put in toolkit?

from ckanext.subscribe.model import Subscription
from ckanext.subscribe import (
    schema,
    dictization,
    email_verification,
)
from ckanext.subscribe import email_auth


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
    :param skip_verification: Doesn't send email - instead it marks the
        subscription as verified. Can be used by sysadmins only.
        (optional, default=False)

    :returns: the newly created subscription
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    _check_access(u'subscribe_signup', context, data_dict)

    data = {
        'email': data_dict['email'],
        'user': context['user']
    }
    if data_dict.get('dataset_id'):
        data['object_type'] = 'dataset'
        dataset_obj = model.Package.get(data_dict['dataset_id'])
        data['object_id'] = dataset_obj.id
    else:
        group_obj = model.Group.get(data_dict['group_id'])
        if group_obj.is_organization:
            data['object_type'] = 'organization'
        else:
            data['object_type'] = 'group'
        data['object_id'] = group_obj.id

    # must be unique combination of email/object_type/object_id
    existing = model.Session.query(Subscription) \
        .filter_by(email=data['email']) \
        .filter_by(object_type=data['object_type']) \
        .filter_by(object_id=data['object_id']) \
        .first()
    if existing:
        # reuse existing subscription
        subscription = existing
    else:
        # create subscription object
        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            rev = model.repo.new_revision()
            rev.author = user
        subscription = dictization.subscription_save(data, context)
        model.repo.commit()

    # send 'confirm your request' email
    if data_dict['skip_verification']:
        subscription.verified = True
        model.repo.commit()
    else:
        email_verification.create_code(subscription)
        email_verification.send_request_email(subscription)

    return dictization.dictize_subscription(subscription, context)


def subscribe_verify(context, data_dict):
    '''Verify (confirm) a subscription

    :param code: Verification code, supplied in the email sent on sign-up

    :returns: the updated subscription
    :rtype: dictionary

    '''
    # This design follows this OWASP guidance:
    # https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html#semantic-validation

    model = context['model']
    user = context['user']

    _check_access(u'subscribe_verify', context, data_dict)

    if not data_dict.get('code'):
        raise p.toolkit.ValidationError(
            'Validation code has not been supplied')
    data = {
        'code': data_dict['code'],
    }
    subscription = model.Session.query(Subscription) \
        .filter_by(verification_code=data['code']) \
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
