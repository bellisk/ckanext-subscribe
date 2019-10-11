import re

import ckan.lib.helpers as h
from ckan.plugins.toolkit import (
    Invalid,
    ObjectNotFound,
    NotAuthorized,
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
        # if not request.POST:
        #     abort(400, _(u'No email address supplied'))

        # validate input
        email = request.POST.get('email')
        if not email:
            abort(400, _(u'No email address supplied'))
        email = email.strip()
        if not re.match(ur'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$', email):
            abort(400, _(u'Email supplied is invalid'))

        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage'
        )

    def manage(self):
        return 'TODO'