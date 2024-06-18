# encoding: utf-8

import re

import ckan.lib.helpers as h
from ckan import model
from ckan.common import g
from ckan.plugins.toolkit import (
    ValidationError,
    ObjectNotFound,
    get_action,
    _,
    request,
    BaseController,
    abort,
    render,
    redirect_to,
    config,
)
from ckan.lib.mailer import MailerException

from ckanext.subscribe import email_auth
from ckanext.subscribe import model as subscribe_model

log = __import__('logging').getLogger(__name__)


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
            'group_id': request.POST.get('group'),
            'organization_id': request.POST.get('organization'),
        }
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            subscription = get_action(u'subscribe_signup')(context, data_dict)
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
            return self._redirect_back_to_subscribe_page_from_request(data_dict)
        except MailerException:
            h.flash_error(_('Error sending email - please contact an '
                            'administrator for help'))
            return self._redirect_back_to_subscribe_page_from_request(data_dict)
        else:
            h.flash_success(
                _('Subscription requested. Please confirm, by clicking in the '
                  'link in the email just sent to you'))
            return self._redirect_back_to_subscribe_page(
                subscription['object_name'], subscription['object_type'])

    def verify_subscription(self):
        data_dict = {'code': request.params.get('code')}
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }

        try:
            subscription = get_action(u'subscribe_verify')(context, data_dict)
        except ValidationError as err:
            h.flash_error(_('Error subscribing: {}'
                            .format(err.error_dict['message'])))
            return redirect_to('home')

        h.flash_success(
            _('Subscription confirmed'))
        code = email_auth.create_code(subscription['email'])

        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage',
            code=code,
        )

    def manage(self):
        code = request.params.get('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return self._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return self._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            u'model': model,
            u'user': site_user['name'],
        }
        subscriptions = \
            get_action(u'subscribe_list_subscriptions')(
                context, {'email': email})
        frequency_options = [
            dict(text=f.name.lower().capitalize().replace(
                     'Immediate', 'Immediately'),
                 value=f.name)
            for f in sorted(subscribe_model.Frequency, key=lambda x: x.value)
        ]
        return render(u'subscribe/manage.html', extra_vars={
            'email': email,
            'code': code,
            'subscriptions': subscriptions,
            'frequency_options': frequency_options,
        })

    def update(self):
        code = request.POST.get('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return self._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return self._request_manage_code_form()

        subscription_id = request.POST.get('id')
        if not subscription_id:
            abort(400, _(u'No id supplied'))
        subscription = model.Session.query(subscribe_model.Subscription) \
            .get(subscription_id)
        if not subscription:
            abort(404, _(u'That subscription ID does not exist.'))
        if subscription.email != email:
            h.flash_error('Code is invalid for that subscription')
            log.debug('Code is invalid for that subscription')
            return self._request_manage_code_form()

        frequency = request.POST.get('frequency')
        if not frequency:
            abort(400, _(u'No frequency supplied'))

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': site_user['name'],
        }
        data_dict = {
            'id': subscription_id,
            'frequency': frequency,
        }
        try:
            get_action(u'subscribe_update')(context, data_dict)
        except ValidationError as err:
            h.flash_error(_('Error updating subscription: {}'
                            .format(err.error_dict['message'])))
        else:
            h.flash_success(_('Subscription updated'))

        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage',
            code=code,
        )

    def unsubscribe(self):
        # allow a GET or POST to do this, so that we can trigger it from a link
        # in an email or a web form
        code = request.params.get('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return self._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return self._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            u'model': model,
            u'user': site_user['name'],
        }
        data_dict = {
            'email': email,
            'dataset_id': request.params.get('dataset'),
            'group_id': request.params.get('group'),
            'organization_id': request.params.get('organization'),
        }
        try:
            object_name, object_type = \
                get_action(u'subscribe_unsubscribe')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before', 'dataset_id',
                                'group_id'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(_('Error unsubscribing: {}'
                            .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(_('Error unsubscribing: {}'.format(err)))
        else:
            h.flash_success(
                _('You are no longer subscribed to this {}'
                  .format(object_type)))
            return self._redirect_back_to_subscribe_page(object_name,
                                                         object_type)
        return self._redirect_back_to_subscribe_page_from_request(data_dict)

    def unsubscribe_all(self):
        # allow a GET or POST to do this, so that we can trigger it from a link
        # in an email or a web form
        code = request.params.get('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return self._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return self._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            u'model': model,
            u'user': site_user['name'],
        }
        data_dict = {
            'email': email,
        }
        try:
            get_action(u'subscribe_unsubscribe_all')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(_('Error unsubscribing: {}'
                            .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(_('Error unsubscribing: {}'.format(err)))
        else:
            h.flash_success(
                _('You are no longer subscribed to notifications from {}'
                  .format(config.get('ckan.site_title'))))
            return redirect_to('home')
        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage',
            code=code,
        )

    def _redirect_back_to_subscribe_page(self, object_name, object_type):
        if object_type == 'dataset':
            return redirect_to(controller='package', action='read',
                               id=object_name)
        elif object_type == 'group':
            return redirect_to(controller='group', action='read',
                               id=object_name)
        elif object_type == 'organization':
            return redirect_to(controller='organization', action='read',
                               id=object_name)
        else:
            return redirect_to('home')

    def _redirect_back_to_subscribe_page_from_request(self, data_dict):
        if data_dict.get('dataset_id'):
            dataset_obj = model.Package.get(data_dict['dataset_id'])
            return redirect_to(
                controller='package', action='read',
                id=dataset_obj.name if dataset_obj else data_dict['dataset_id']
            )
        elif data_dict.get('group_id'):
            group_obj = model.Group.get(data_dict['group_id'])
            controller = 'organization' \
                if group_obj and group_obj.is_organization \
                else 'group'
            return redirect_to(
                controller=controller, action='read',
                id=group_obj.name if group_obj else data_dict['group_id'])
        else:
            return redirect_to('home')

    def _request_manage_code_form(self):
        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='request_manage_code',
        )

    def request_manage_code(self):
        email = request.POST.get('email')
        if not email:
            return render(u'subscribe/request_manage_code.html', extra_vars={})

        context = {
            u'model': model,
        }
        try:
            get_action(u'subscribe_request_manage_code')(
                context, dict(email=email))
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(_('Error requesting code: {}'
                            .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(_('Error requesting code: {}'.format(err)))
        except MailerException:
            h.flash_error(_('Error sending email - please contact an '
                            'administrator for help'))
        else:
            h.flash_success(
                _('An access link has been emailed to: {}'
                  .format(email)))
            return redirect_to('home')
        return render(u'subscribe/request_manage_code.html',
                      extra_vars={'email': email})
