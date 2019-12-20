import ckan.plugins as p
from ckan.common import _

get_validator = p.toolkit.get_validator
Invalid = p.toolkit.Invalid
email = get_validator('email_validator')
ignore_empty = get_validator('ignore_empty')
package_id_or_name_exists = get_validator('package_id_or_name_exists')
group_id_or_name_exists = get_validator('group_id_or_name_exists')
ignore_missing = get_validator('ignore_missing')
boolean_validator = get_validator('boolean_validator')

def one_package_or_group(key, data, errors, context):
    if data[('dataset_id',)] and data[('group_id',)]:
        raise Invalid(_('Must not specify both "dataset_id" and "group_id"'))
    if not data[('dataset_id',)] and not data[('group_id',)]:
        raise Invalid(_('Must specify either "dataset_id" or "group_id"'))

def subscribe_schema():
    return {
        u'__before': [one_package_or_group],
        u'dataset_id': [ignore_empty, package_id_or_name_exists],
        u'group_id': [ignore_empty, group_id_or_name_exists],
        u'email': [email],
        u'skip_verification': [boolean_validator],
    }
