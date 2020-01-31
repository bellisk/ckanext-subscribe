# encoding: utf-8

import ckan.plugins as p
from ckan.common import _

from ckanext.subscribe.model import Subscription, Frequency

get_validator = p.toolkit.get_validator
Invalid = p.toolkit.Invalid
email = get_validator('email_validator')
ignore_empty = get_validator('ignore_empty')
package_id_or_name_exists = get_validator('package_id_or_name_exists')
group_id_or_name_exists = get_validator('group_id_or_name_exists')
ignore_missing = get_validator('ignore_missing')
boolean_validator = get_validator('boolean_validator')


def one_package_or_group_or_org(key, data, errors, context):
    num_objects_specified = len(filter(None, [data[('dataset_id',)],
                                              data[('group_id',)],
                                              data[('organization_id',)]]))
    if num_objects_specified > 1:
        raise Invalid(_('Must not specify more than one of: "dataset_id", '
                        '"group_id" or "organization_id"'))
    if num_objects_specified < 1:
        raise Invalid(_('Must specify one of: "dataset_id", '
                        '"group_id" or "organization_id"'))


def frequency_name_to_int(name, context):
    try:
        return Frequency[name.upper()].value
    except KeyError:
        raise Invalid(_('Frequency must be one of: {}'
                        .format(' '.join(f.name.lower() for f in Frequency))))


def subscribe_schema():
    return {
        u'__before': [one_package_or_group_or_org],
        u'dataset_id': [ignore_empty, package_id_or_name_exists],
        u'group_id': [ignore_empty, group_id_or_name_exists],
        u'organization_id': [ignore_empty, group_id_or_name_exists],
        u'email': [email],
        u'frequency': [ignore_empty, frequency_name_to_int],
        u'skip_verification': [boolean_validator],
    }


def update_schema():
    return {
        u'id': [subscription_id_exists],
        u'frequency': [ignore_empty, frequency_name_to_int],
    }


def unsubscribe_schema():
    return {
        u'__before': [one_package_or_group_or_org],
        u'dataset_id': [ignore_empty, package_id_or_name_exists],
        u'group_id': [ignore_empty, group_id_or_name_exists],
        u'organization_id': [ignore_empty, group_id_or_name_exists],
        u'email': [email],
    }


def unsubscribe_all_schema():
    return {
        u'email': [email],
    }


def request_manage_code_schema():
    return {
        u'email': [email],
    }


def subscription_id_exists(id_, context):
    '''
    Raises Invalid if a subscription identified by the id cannot be found.
    '''
    model = context['model']
    result = model.Session.query(Subscription).get(id_)
    if not result:
        raise Invalid(_('That subscription ID does not exist.'))
    return id_
