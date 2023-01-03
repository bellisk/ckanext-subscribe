# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.subscribe import action
from ckanext.subscribe import auth
from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.interfaces import ISubscribe


class SubscribePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(ISubscribe, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'subscribe')

        subscribe_model.setup()

    # IRoutes

    def before_map(self, map):
        controller = 'ckanext.subscribe.controller:SubscribeController'
        map.connect('signup', '/subscribe/signup',
                    controller=controller, action='signup')
        map.connect('verify', '/subscribe/verify',
                    controller=controller, action='verify_subscription')
        map.connect('update', '/subscribe/update',
                    controller=controller, action='update')
        map.connect('manage', '/subscribe/manage',
                    controller=controller, action='manage')
        map.connect('unsubscribe', '/subscribe/unsubscribe',
                    controller=controller, action='unsubscribe')
        map.connect('unsubscribe_all', '/subscribe/unsubscribe-all',
                    controller=controller, action='unsubscribe_all')
        map.connect('request_manage_code', '/subscribe/request_manage_code',
                    controller=controller, action='request_manage_code')
        return map

    def after_map(self, map):
        return map

    # IActions

    def get_actions(self):
        return {
            'subscribe_signup': action.subscribe_signup,
            'subscribe_verify': action.subscribe_verify,
            'subscribe_update': action.subscribe_update,
            'subscribe_list_subscriptions':
            action.subscribe_list_subscriptions,
            'subscribe_unsubscribe': action.subscribe_unsubscribe,
            'subscribe_unsubscribe_all': action.subscribe_unsubscribe_all,
            'subscribe_request_manage_code':
            action.subscribe_request_manage_code,
            'subscribe_send_any_notifications':
            action.subscribe_send_any_notifications,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'subscribe_signup': auth.subscribe_signup,
            'subscribe_verify': auth.subscribe_verify,
            'subscribe_update': auth.subscribe_update,
            'subscribe_list_subscriptions':
            auth.subscribe_list_subscriptions,
            'subscribe_unsubscribe': auth.subscribe_unsubscribe,
            'subscribe_unsubscribe_all': auth.subscribe_unsubscribe_all,
            'subscribe_request_manage_code':
            auth.subscribe_request_manage_code,
            'subscribe_send_any_notifications':
            auth.subscribe_send_any_notifications,
        }
