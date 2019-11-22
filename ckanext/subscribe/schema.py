import ckan.plugins as p


get_validator = p.toolkit.get_validator
email = get_validator('email_validator')
ignore_empty = get_validator('ignore_empty')
package_id_or_name_exists = get_validator('package_id_or_name_exists')
group_id_or_name_exists = get_validator('group_id_or_name_exists')

def one_package_or_group(key, data, errors, context):
    if data['package'] and data['group']:
        raise Invalid(_('Must not specify both "package" and "group"'))
    if not data['package'] and not data['group']:
        raise Invalid(_('Must specify either "package" or "group"'))

def subscribe_schema():
    return {
        u'__before': [one_package_or_group],
        u'package': [ignore_empty, package_id_or_name_exists],
        u'group': [ignore_empty, group_id_or_name_exists],
        u'email': [email],
    }
