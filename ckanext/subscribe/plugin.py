# encoding: utf-8

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk

import ckanext.subscribe.helpers as subscribe_helpers
from ckanext.subscribe import action, auth
from ckanext.subscribe.blueprints import subscribe_blueprint
from ckanext.subscribe.interfaces import ISubscribe


class SubscribePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(ISubscribe, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")
        # Register WebAssets
        tk.add_resource("assets", "subscribe")

    # IActions

    def get_actions(self):
        return {
            "subscribe_signup": action.subscribe_signup,
            "subscribe_verify": action.subscribe_verify,
            "subscribe_update": action.subscribe_update,
            "subscribe_list_subscriptions": action.subscribe_list_subscriptions,
            "subscribe_unsubscribe": action.subscribe_unsubscribe,
            "subscribe_unsubscribe_all": action.subscribe_unsubscribe_all,
            "subscribe_request_manage_code": action.subscribe_request_manage_code,
            "subscribe_send_any_notifications": action.subscribe_send_any_notifications,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            "subscribe_signup": auth.subscribe_signup,
            "subscribe_verify": auth.subscribe_verify,
            "subscribe_update": auth.subscribe_update,
            "subscribe_list_subscriptions": auth.subscribe_list_subscriptions,
            "subscribe_unsubscribe": auth.subscribe_unsubscribe,
            "subscribe_unsubscribe_all": auth.subscribe_unsubscribe_all,
            "subscribe_request_manage_code": auth.subscribe_request_manage_code,
            "subscribe_send_any_notifications": auth.subscribe_send_any_notifications,
        }

    # ITemplateHelpers
    def get_helpers(self):
        """Provide template helper functions"""

        return {
            "get_recaptcha_publickey": subscribe_helpers.get_recaptcha_publickey,
            "apply_recaptcha": subscribe_helpers.apply_recaptcha,
        }

    # IBlueprint
    def get_blueprint(self):
        return [subscribe_blueprint]
