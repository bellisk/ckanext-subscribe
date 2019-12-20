# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.subscribe import action
from ckanext.subscribe import auth


class SubscribePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'subscribe')

    # IRoutes

    def before_map(self, map):
        controller = 'ckanext.subscribe.controller:SubscribeController'
        map.connect('signup', '/subscribe/signup',
            controller=controller, action='signup')
        map.connect('verify', '/subscribe/verify',
            controller=controller, action='verify_subscription')
        map.connect('manage', '/subscribe/manage',
            controller=controller, action='manage')
        return map

    def after_map(self, map):
        return map

    # IActions

    def get_actions(self):
        return {
            'subscribe_signup': action.subscribe_signup,
            'subscribe_verify': action.subscribe_verify,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'subscribe_signup': auth.subscribe_signup,
            'subscribe_verify': auth.subscribe_verify,
        }