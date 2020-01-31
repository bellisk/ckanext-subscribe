# encoding: utf-8

from ckan.plugins.toolkit import _, check_access, auth_allow_anonymous_access


@auth_allow_anonymous_access
def subscribe_signup(context, data_dict):
    model = context['model']
    dataset_id = data_dict.get('dataset_id')
    group_id = data_dict.get('group_id')
    skip_verification = data_dict.get('skip_verification')

    # check dataset can be read
    if dataset_id:
        pkg = model.Package.get(dataset_id)
        check_access('package_show', context, {'id': pkg.id})

    elif group_id:
        group = model.Group.get(group_id)
        check_access('group_show', context, {'id': group.id})
    else:
        return {'success': False,
                'msg': _(u'No object specified')}

    if skip_verification and \
            skip_verification not in (None, 0, False) and \
            skip_verification not in ('false', 'f', 'no', 'n', '0'):
        # sysadmins only
        return {'success': False,
                'msg': _(u'Not authorized to skip verification')}

    return {'success': True}


@auth_allow_anonymous_access
def subscribe_verify(context, data_dict):
    return {'success': True}


def subscribe_list_subscriptions(context, data_dict):
    # sysadmins only
    return {'success': False}


def subscribe_unsubscribe(context, data_dict):
    # sysadmins only
    return {'success': False}


def subscribe_unsubscribe_all(context, data_dict):
    # sysadmins only
    return {'success': False}


@auth_allow_anonymous_access
def subscribe_manage(context, data_dict):
    # code auth is done in the action function, to allow you to request a code
    return {'success': True}


@auth_allow_anonymous_access
def subscribe_request_manage_code(context, data_dict):
    return {'success': True}


def subscribe_send_any_notifications(context, data_dict):
    # sysadmins only
    return {'success': False}


def subscribe_update(context, data_dict):
    # sysadmins only
    return {'success': False}
