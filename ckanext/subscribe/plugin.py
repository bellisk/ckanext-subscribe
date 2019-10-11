import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import blueprint
import helpers


class SubscribePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'subscribe')

    # IBlueprint

    def get_blueprint(self):
        return blueprint.subscribe_blueprint
        # # Add plugin url rule to Blueprint object
        # blueprint.add_url_rule('/pylons_and_flask', 'flask_plugin_view',
        #                        flask_plugin_view)

        # blueprint.add_url_rule('/simple_flask', 'flask_plugin_view',
        #                        flask_plugin_view)
