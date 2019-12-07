# encoding: utf-8

from ckan.plugins.toolkit import _, check_access, auth_allow_anonymous_access


@auth_allow_anonymous_access
def subscribe_signup(context, data_dict):
    model = context['model']
    dataset_id = data_dict.get('dataset_id')
    group_id = data_dict.get('group_id')

    # check dataset can be read
    if dataset_id:
        pkg = model.Package.get(dataset_id)
        authorized = check_access('package_show', context, {'id': pkg.id})
        if not authorized:
            return {'success': False,
                    'msg': _(u'Not authorized to read dataset {}')
                        .format(dataset_id)}
    elif group_id:
        group = model.Group.get(group_id)
        authorized = check_access('group_show', context, {'id': group.id})
        if not authorized:
            return {'success': False,
                    'msg': _(u'Not authorized to read group {}')
                        .format(dataset_id)}
    else:
        return {'success': False,
                'msg': _(u'No object specified')}

    return {'success': True}
