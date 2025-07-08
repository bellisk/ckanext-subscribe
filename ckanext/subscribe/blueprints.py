import re

import ckan.lib.helpers as h
from ckan import model
from ckan.common import g
from ckan.lib.mailer import MailerException
from ckan.plugins.toolkit import (
    BaseController,
    ObjectNotFound,
    ValidationError,
    _,
    abort,
    config,
    get_action,
    redirect_to,
    render,
    request,
)
from flask import Blueprint

from ckanext.subscribe import email_auth
from ckanext.subscribe import model as subscribe_model

log = __import__("logging").getLogger(__name__)

subscribe_blueprint = Blueprint("subscribe", __name__, url_prefix="/subscribe")


def _redirect_back_to_subscribe_page(object_name, object_type):
    if object_type == "dataset":
        return redirect_to("package.read", id=object_name)
    elif object_type == "group":
        return redirect_to("group.read", id=object_name)
    elif object_type == "organization":
        return redirect_to("organization.read", id=object_name)
    else:
        return redirect_to("home")


def _redirect_back_to_subscribe_page_from_request(data_dict):
    if data_dict.get("dataset_id"):
        dataset_obj = model.Package.get(data_dict["dataset_id"])
        return redirect_to(
            "package.read",
            id=dataset_obj.name if dataset_obj else data_dict["dataset_id"],
        )
    elif data_dict.get("group_id"):
        group_obj = model.Group.get(data_dict["group_id"])
        group_type = (
            "organization" if group_obj and group_obj.is_organization else "group"
        )
        return redirect_to(
            f"{group_type}.read",
            id=group_obj.name if group_obj else data_dict["group_id"],
        )
    else:
        return redirect_to("home")


def _request_manage_code_form():
    return redirect_to(
        "subscribe.request_manage_code",
    )


def signup():
    # validate inputs
    email = request.POST.get("email")
    if not email:
        abort(400, _("No email address supplied"))
    email = email.strip()
    # pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
    email_re = (
        r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )
    if not re.match(email_re, email):
        abort(400, _("Email supplied is invalid"))

    # create subscription
    data_dict = {
        "email": email,
        "dataset_id": request.POST.get("dataset"),
        "group_id": request.POST.get("group"),
        "organization_id": request.POST.get("organization"),
        "g_recaptcha_response": request.POST.get("g-recaptcha-response"),
    }
    context = {
        "model": model,
        "session": model.Session,
        "user": g.user,
        "auth_user_obj": g.userobj,
    }
    try:
        subscription = get_action("subscribe_signup")(context, data_dict)
    except ValidationError as err:
        error_messages = []
        for key_ignored in ("message", "__before", "dataset_id", "group_id"):
            if key_ignored in err.error_dict:
                error_messages.extend(err.error_dict.pop(key_ignored))
        if err.error_dict:
            error_messages.append(repr(err.error_dict))
        h.flash_error(_(f"Error subscribing: {'; '.join(error_messages)}"))
        return _redirect_back_to_subscribe_page_from_request(data_dict)
    except MailerException:
        h.flash_error(
            _("Error sending email - please contact an " "administrator for help")
        )
        return _redirect_back_to_subscribe_page_from_request(data_dict)
    else:
        h.flash_success(
            _(
                "Subscription requested. Please confirm, by clicking in the "
                "link in the email just sent to you"
            )
        )
        return _redirect_back_to_subscribe_page(
            subscription["object_name"], subscription["object_type"]
        )


def verify_subscription():
    data_dict = {"code": request.params.get("code")}
    context = {
        "model": model,
        "session": model.Session,
        "user": g.user,
        "auth_user_obj": g.userobj,
    }

    try:
        subscription = get_action("subscribe_verify")(context, data_dict)
    except ValidationError as err:
        h.flash_error(_(f"Error subscribing: {err.error_dict['message']}"))
        return redirect_to("home")

    h.flash_success(_("Subscription confirmed"))
    code = email_auth.create_code(subscription["email"])

    return redirect_to(
        controller="ckanext.subscribe.controller:SubscribeController",
        action="manage",
        code=code,
    )


def manage():
    code = request.params.get("code")
    if not code:
        h.flash_error("Code not supplied")
        log.debug("No code supplied")
        return _request_manage_code_form()
    try:
        email = email_auth.authenticate_with_code(code)
    except ValueError as exp:
        h.flash_error(f"Code is invalid: {exp}")
        log.debug(f"Code is invalid: {exp}")
        return _request_manage_code_form()

    # user has done auth, but it's an email rather than a ckan user, so
    # use site_user
    site_user = get_action("get_site_user")({"model": model, "ignore_auth": True}, {})
    context = {
        "model": model,
        "user": site_user["name"],
    }
    subscriptions = get_action("subscribe_list_subscriptions")(
        context, {"email": email}
    )
    frequency_options = [
        dict(
            text=f.name.lower().capitalize().replace("Immediate", "Immediately"),
            value=f.name,
        )
        for f in sorted(subscribe_model.Frequency, key=lambda x: x.value)
    ]
    return render(
        "subscribe/manage.html",
        extra_vars={
            "email": email,
            "code": code,
            "subscriptions": subscriptions,
            "frequency_options": frequency_options,
        },
    )


def update():
    code = request.POST.get("code")
    if not code:
        h.flash_error("Code not supplied")
        log.debug("No code supplied")
        return _request_manage_code_form()
    try:
        email = email_auth.authenticate_with_code(code)
    except ValueError as exp:
        h.flash_error(f"Code is invalid: {exp}")
        log.debug(f"Code is invalid: {exp}")
        return _request_manage_code_form()

    subscription_id = request.POST.get("id")
    if not subscription_id:
        abort(400, _("No id supplied"))
    subscription = model.Session.query(subscribe_model.Subscription).get(
        subscription_id
    )
    if not subscription:
        abort(404, _("That subscription ID does not exist."))
    if subscription.email != email:
        h.flash_error("Code is invalid for that subscription")
        log.debug("Code is invalid for that subscription")
        return _request_manage_code_form()

    frequency = request.POST.get("frequency")
    if not frequency:
        abort(400, _("No frequency supplied"))

    # user has done auth, but it's an email rather than a ckan user, so
    # use site_user
    site_user = get_action("get_site_user")({"model": model, "ignore_auth": True}, {})
    context = {
        "model": model,
        "session": model.Session,
        "user": site_user["name"],
    }
    data_dict = {
        "id": subscription_id,
        "frequency": frequency,
    }
    try:
        get_action("subscribe_update")(context, data_dict)
    except ValidationError as err:
        h.flash_error(_(f"Error updating subscription: {err.error_dict['message']}"))
    else:
        h.flash_success(_("Subscription updated"))

    return redirect_to(
        controller="ckanext.subscribe.controller:SubscribeController",
        action="manage",
        code=code,
    )


def unsubscribe():
    # allow a GET or POST to do this, so that we can trigger it from a link
    # in an email or a web form
    code = request.params.get("code")
    if not code:
        h.flash_error("Code not supplied")
        log.debug("No code supplied")
        return _request_manage_code_form()
    try:
        email = email_auth.authenticate_with_code(code)
    except ValueError as exp:
        h.flash_error(f"Code is invalid: {exp}")
        log.debug(f"Code is invalid: {exp}")
        return _request_manage_code_form()

    # user has done auth, but it's an email rather than a ckan user, so
    # use site_user
    site_user = get_action("get_site_user")({"model": model, "ignore_auth": True}, {})
    context = {
        "model": model,
        "user": site_user["name"],
    }
    data_dict = {
        "email": email,
        "dataset_id": request.params.get("dataset"),
        "group_id": request.params.get("group"),
        "organization_id": request.params.get("organization"),
    }
    try:
        object_name, object_type = get_action("subscribe_unsubscribe")(
            context, data_dict
        )
    except ValidationError as err:
        error_messages = []
        for key_ignored in ("message", "__before", "dataset_id", "group_id"):
            if key_ignored in err.error_dict:
                error_messages.extend(err.error_dict.pop(key_ignored))
        if err.error_dict:
            error_messages.append(repr(err.error_dict))
        h.flash_error(_(f"Error unsubscribing: {'; '.join(error_messages)}"))
    except ObjectNotFound as err:
        h.flash_error(_(f"Error unsubscribing: {err}"))
    else:
        h.flash_success(_(f"You are no longer subscribed to this {object_type}"))
        return _redirect_back_to_subscribe_page(object_name, object_type)
    return _redirect_back_to_subscribe_page_from_request(data_dict)


def unsubscribe_all():
    # allow a GET or POST to do this, so that we can trigger it from a link
    # in an email or a web form
    code = request.params.get("code")
    if not code:
        h.flash_error("Code not supplied")
        log.debug("No code supplied")
        return _request_manage_code_form()
    try:
        email = email_auth.authenticate_with_code(code)
    except ValueError as exp:
        h.flash_error(f"Code is invalid: {exp}")
        log.debug(f"Code is invalid: {exp}")
        return _request_manage_code_form()

    # user has done auth, but it's an email rather than a ckan user, so
    # use site_user
    site_user = get_action("get_site_user")({"model": model, "ignore_auth": True}, {})
    context = {
        "model": model,
        "user": site_user["name"],
    }
    data_dict = {
        "email": email,
    }
    try:
        get_action("subscribe_unsubscribe_all")(context, data_dict)
    except ValidationError as err:
        error_messages = []
        for key_ignored in ("message", "__before"):
            if key_ignored in err.error_dict:
                error_messages.extend(err.error_dict.pop(key_ignored))
        if err.error_dict:
            error_messages.append(repr(err.error_dict))
        h.flash_error(_(f"Error unsubscribing: {'; '.join(error_messages)}"))
    except ObjectNotFound as err:
        h.flash_error(_(f"Error unsubscribing: {err}"))
    else:
        h.flash_success(
            _(
                f"You are no longer subscribed to notifications from "
                f"{config.get('ckan.site_title')}"
            )
        )
        return redirect_to("home")
    return redirect_to(
        controller="ckanext.subscribe.controller:SubscribeController",
        action="manage",
        code=code,
    )


def request_manage_code():
    email = request.POST.get("email")
    if not email:
        return render("subscribe/request_manage_code.html", extra_vars={})

    context = {
        "model": model,
    }
    try:
        get_action("subscribe_request_manage_code")(context, dict(email=email))
    except ValidationError as err:
        error_messages = []
        for key_ignored in ("message", "__before"):
            if key_ignored in err.error_dict:
                error_messages.extend(err.error_dict.pop(key_ignored))
        if err.error_dict:
            error_messages.append(repr(err.error_dict))
        h.flash_error(_(f"Error requesting code: {'; '.join(error_messages)}"))
    except ObjectNotFound as err:
        h.flash_error(_(f"Error requesting code: {err}"))
    except MailerException:
        h.flash_error(
            _("Error sending email - please contact an " "administrator for help")
        )
    else:
        h.flash_success(_(f"An access link has been emailed to: {email}"))
        return redirect_to("home")
    return render("subscribe/request_manage_code.html", extra_vars={"email": email})


subscribe_blueprint.add_url_rule("/signup", view_func=signup)
subscribe_blueprint.add_url_rule("/verify", view_func=verify_subscription)
subscribe_blueprint.add_url_rule("/manage", view_func=manage)
subscribe_blueprint.add_url_rule("/update", view_func=update)
subscribe_blueprint.add_url_rule("/unsubscribe", view_func=unsubscribe)
subscribe_blueprint.add_url_rule("/unsubscribe_all", view_func=unsubscribe_all)
subscribe_blueprint.add_url_rule("/request_manage_code", view_func=request_manage_code)
