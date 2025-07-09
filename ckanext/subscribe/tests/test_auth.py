import ckan.logic as logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest
from ckan import model


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSubscribeSignupToDataset(object):

    def test_no_user_specified(self):
        dataset = factories.Dataset(state="deleted")
        context = {"model": model}
        context["user"] = ""

        with pytest.raises(logic.NotAuthorized) as exc_info:
            helpers.call_auth(
                "subscribe_signup", context=context, dataset_id=dataset["name"]
            )
        assert "not authorized to read package" in str(exc_info.value)

    def test_deleted_dataset_not_subscribable(self):
        factories.User(name="fred")
        dataset = factories.Dataset(state="deleted")
        context = {"model": model}
        context["user"] = "fred"

        with pytest.raises(logic.NotAuthorized) as exc_info:
            helpers.call_auth(
                "subscribe_signup", context=context, dataset_id=dataset["name"]
            )
        assert "User fred not authorized to read package" in str(exc_info.value)

    def test_private_dataset_is_subscribable_to_editor(self):
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org["id"], private=True)
        context = {"model": model}
        context["user"] = "fred"

        ret = helpers.call_auth(
            "subscribe_signup", context=context, dataset_id=dataset["name"]
        )
        assert ret

    def test_private_dataset_is_not_subscribable_to_public(self):
        factories.User(name="fred")
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"], private=True)
        context = {"model": model}
        context["user"] = "fred"

        with pytest.raises(logic.NotAuthorized) as exc_info:
            helpers.call_auth(
                "subscribe_signup", context=context, dataset_id=dataset["name"]
            )
        assert "User fred not authorized to read package" in str(exc_info.value)

    def test_admin_cant_skip_verification(self):
        # (only sysadmin can)
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org["id"])
        context = {"model": model}
        context["user"] = "fred"

        with pytest.raises(logic.NotAuthorized) as exc_info:
            helpers.call_auth(
                "subscribe_signup",
                context=context,
                dataset_id=dataset["name"],
                skip_verification=True,
            )
        assert "Not authorized to skip verification" in str(exc_info.value)


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSubscribeListSubscriptions(object):
    def test_admin_cant_use_it(self):
        # (only sysadmin can)
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        factories.Organization(users=[fred])
        context = {"model": model}
        context["user"] = "fred"

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "subscribe_list_subscriptions", context=context, email=fred["email"]
            )


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSubscribeUnsubscribe(object):
    def test_admin_cant_use_it(self):
        # (only sysadmin can)
        fred = factories.User(name="fred")
        fred["capacity"] = "editor"
        factories.Organization(users=[fred])
        context = {"model": model}
        context["user"] = "fred"

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth(
                "subscribe_unsubscribe", context=context, email=fred["email"]
            )
