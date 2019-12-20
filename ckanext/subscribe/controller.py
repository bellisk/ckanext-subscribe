# encoding: utf-8

import re

import ckan.lib.helpers as h
from ckan import model
from ckan.common import g
from ckan.plugins.toolkit import (
    Invalid,
    ObjectNotFound,
    NotAuthorized,
    ValidationError,
    get_action,
    get_validator,
    _,
    request,
    response,
    BaseController,
    abort,
    render,
    c,
    h,
    config,
    redirect_to,
)

class SubscribeController(BaseController):
    def signup(self):
        # validate inputs
        email = request.POST.get('email')
        if not email:
            abort(400, _(u'No email address supplied'))
        email = email.strip()
        # pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
        email_re = r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(email_re, email):
            abort(400, _(u'Email supplied is invalid'))

        # create subscription
        data_dict = {
            'email': email,
            'dataset_id': request.POST.get('dataset'),
            'group_id': request.POST.get('group')
        }
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            get_action(u'subscribe_signup')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before', 'dataset_id',
                                'group_id'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(_('Error subscribing: {}'
                            .format('; '.join(error_messages))))
        else:
            h.flash_success(
                _('Subscription requested. Please confirm, by clicking in the '
                  'link in the email just sent to you'))
        return self._redirect_back_to_subscribe_page(context, data_dict)

    def verify_subscription(self):
        data_dict = {'code': request.params.get('code')}
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }

        try:
            get_action(u'subscribe_verify')(context, data_dict)
        except ValidationError as err:
            h.flash_error(_('Error subscribing: {}'
                            .format(err.error_dict['message'])))
            return redirect_to('home')

        h.flash_success(
            _('Subscription confirmed'))

        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage',
        )

    def manage(self):
        return render(u'subscribe/manage.html', extra_vars={})

    def _redirect_back_to_subscribe_page(self, context, data_dict):
        if data_dict.get('dataset_id'):
            return redirect_to(controller='package', action='read',
                               id=data_dict['dataset_id'])
        elif data_dict.get('group_id'):
            group_obj = model.Group.get(data_dict['group_id'])
            controller = 'organization' \
                if group_obj and group_obj.is_organization \
                else 'group'
            return redirect_to(controller=controller, action='read',
                               id=data_dict['group_id'])
        else:
            return redirect_to('home')
