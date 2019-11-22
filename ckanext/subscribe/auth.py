# encoding: utf-8

from ckan.plugins.toolkit import _, check_access


def subscribe_signup(context, data_dict):
    model = context['model']
    package_id = data_dict.get('package_id')
    group_id = data_dict.get('group_id')

    # check package can be read
    if package_id:
        pkg = model.Package.get(package_id)
        authorized = check_access('package_show', context, {'id': pkg.id})
        if not authorized:
            return {'success': False,
                    'msg': _(u'Not authorized to read dataset {}')
                        .format(package_id)}
    elif group_id:
        group = model.Group.get(group_id)
        authorized = check_access('group_show', context, {'id': group.id})
        if not authorized:
            return {'success': False,
                    'msg': _(u'Not authorized to read group {}')
                        .format(package_id)}
    else:
        return {'success': False,
                'msg': _(u'No object specified')}

    return {'success': True}
