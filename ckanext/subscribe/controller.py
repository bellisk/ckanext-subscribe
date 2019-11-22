# encoding: utf-8

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
        # validate inputs
        email = request.POST.get('email')
        if not email:
            abort(400, _(u'No email address supplied'))
        email = email.strip()
        # pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
        email_re = ur"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
            ur"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
            ur"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(email_re, email):
            abort(400, _(u'Email supplied is invalid'))

        return redirect_to(
            controller='ckanext.subscribe.controller:SubscribeController',
            action='manage'
        )

    def manage(self):
        return 'TODO'