import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import blueprint
import helpers


class SubscribePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IRoutes)

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
        map.connect('manage', '/subscribe/manage',
            controller=controller, action='manage')
        return map

    def after_map(self, map):
        return map


    # def get_blueprint(self):
    #     return blueprint.subscribe_blueprint
