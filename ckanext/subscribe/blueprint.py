from flask import Blueprint

from ckan.plugins.toolkit import render


subscribe_blueprint = Blueprint(u'subscribe', __name__,
                                url_prefix=u'/subscribe')


@subscribe_blueprint.route(u'/signup', methods=[u'POST'])
def signup(*args, **kwargs):
    # Do some stuff
    extra_vars = {}
    return render('ckanext/subscribe/signup.html', extra_vars)

        #     # Add plugin url rule to Blueprint object
        # blueprint.add_url_rule('/pylons_and_flask', 'flask_plugin_view',
        #                        flask_plugin_view)

        # blueprint.add_url_rule('/simple_flask', 'flask_plugin_view',
        #                        flask_plugin_view)

