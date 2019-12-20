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


log = logging.getLogger(__name__)
_check_access = p.toolkit.check_access
NotFound = p.toolkit.ObjectNotFound


@validate(schema.subscribe_schema)
def subscribe_signup(context, data_dict):
    '''Signup to get notifications of email. Causes a email to be sent,
    containing a verification link.

    :param email: Email address to get notifications to
    :param package_id: Package name or id to get notifications about
                       (specify package_id or group_id - not both)
    :param group_id: Group or organization name or id to get notifications
                     about (specify package_id or group_id - not both)
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

    # send confirmation/verification email
    if data_dict['skip_verification']:
        subscription.verified = True
        model.repo.commit()
    else:
        email_verification.send_confirmation_email(subscription)

    return dictization.dictize_subscription(subscription, context)


def subscribe_validate(context, data_dict):
    '''Validate (confirm) a subscription

    :param code: Validation code, supplied in the email sent on sign-up

    :returns: the updated subscription
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    _check_access(u'subscribe_validate', context, data_dict)

    data = {
        'code': data_dict['code'],
    }
    subscription = Subscription.get(data_dict['code'])
    if not subscription:
        raise p.toolkit.ValidationError(
            'That validation code is not recognized')
    if subscription.expiry > datetime.datetime.now():
        raise p.toolkit.ValidationError(
            'That validation code has expired')

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
        # create subscription

        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            rev = model.repo.new_revision()
            rev.author = user

        subscription = dictization.subscription_save(data, context)

        if not context.get('defer_commit'):
            model.repo.commit()

    dictized_subscription = dictization.dictize_subscription
    return dictized_subscription(subscription, context)
