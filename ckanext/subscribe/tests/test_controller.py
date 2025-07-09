# encoding: utf-8

import datetime

import mock
import pytest
from ckan.tests.factories import Dataset, Group, Organization

from ckanext.subscribe import email_auth
from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.tests.factories import Subscription, SubscriptionLowLevel


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSignupSubmit(object):
    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_signup_to_dataset_ok(self, mock_mailer, app):
        dataset = Dataset()
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com", "dataset": dataset["id"]},
            status=302,
        )
        assert mock_mailer.called
        assert (
            response.location
            == f"http://test.ckan.net/dataset/{dataset['name']}?__no_cache__=True"
        )

    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_signup_to_group_ok(self, mock_mailer, app):
        group = Group()
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com", "group": group["id"]},
            status=302,
        )
        assert mock_mailer.called
        assert (
            response.location
            == f"http://test.ckan.net/group/{group['name']}?__no_cache__=True"
        )

    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_signup_to_org_ok(self, mock_mailer, app):
        org = Organization()
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com", "group": org["id"]},
            status=302,
        )
        assert mock_mailer.called
        assert (
            response.location
            == f"http://test.ckan.net/organization/{org['name']}?__no_cache__=True"
        )

    def test_get_not_post(self, app):
        response = app.get("/subscribe/signup", status=400)
        response.mustcontain("No email address supplied")

    def test_object_not_specified(self, app):
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com"},  # no dataset or group
            status=302,
        ).follow()
        response.mustcontain(
            "Error subscribing: Must specify one of: " "&#34;dataset_id&#34;"
        )

    def test_dataset_missing(self, app):
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com", "dataset": "unknown"},
        ).follow(status=404)
        response.mustcontain("Dataset not found")

    def test_group_missing(self, app):
        response = app.post(
            "/subscribe/signup",
            params={"email": "bob@example.com", "group": "unknown"},
        ).follow(status=404)
        response.mustcontain("Group not found")

    def test_empty_email(self, app):
        dataset = Dataset()
        response = app.post(
            "/subscribe/signup",
            params={"email": "", "dataset": dataset["id"]},
            status=400,
        )
        response.mustcontain("No email address supplied")

    def test_bad_email(self, app):
        dataset = Dataset()
        response = app.post(
            "/subscribe/signup",
            params={"email": "invalid email", "dataset": dataset["id"]},
            status=400,
        )
        response.mustcontain("Email supplied is invalid")


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestVerifySubscription(object):
    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_verify_dataset_ok(self, mock_mailer, app):
        dataset = Dataset()
        SubscriptionLowLevel(
            object_id=dataset["id"],
            object_type="dataset",
            email="bob@example.com",
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code="verify_code",
            verification_code_expires=datetime.datetime.now()
            + datetime.timedelta(hours=1),
        )

        response = app.post(
            "/subscribe/verify", params={"code": "verify_code"}, status=302
        )
        assert mock_mailer.called
        assert response.location.startswith(
            "http://test.ckan.net/subscribe/manage?code="
        )

    def test_wrong_code(self, app):
        response = app.post(
            "/subscribe/verify", params={"code": "unknown_code"}, status=302
        )
        assert response.location == "http://test.ckan.net/?__no_cache__=True"


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestManage(object):
    def test_basic(self, app):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset["id"],
            email="bob@example.com",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get("/subscribe/manage", params={"code": code}, status=200)

        assert dataset["title"] in response.body.decode("utf8")

    def test_no_code(self, app):
        response = app.get("/subscribe/manage", params={"code": ""}, status=302)

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )

    def test_bad_code(self, app):
        response = app.get("/subscribe/manage", params={"code": "bad-code"}, status=302)

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUpdate(object):
    def test_submit(self, app):
        subscription = Subscription(
            email="bob@example.com",
            frequency="WEEKLY",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.post(
            "/subscribe/update",
            params={"code": code, "id": subscription["id"], "frequency": "daily"},
            status=302,
        )

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/manage?code="
        )
        response = response.follow()
        assert '<option value="DAILY" selected>' in response.body.decode("utf8")

    def test_form_submit(self, app):
        Subscription(
            email="bob@example.com",
            frequency="WEEKLY",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get("/subscribe/manage", params={"code": code}, status=200)
        form = response.forms["frequency-form"]
        form["frequency"] = "IMMEDIATE"
        response = app.post("/subscribe/manage", data=form, headers={})

        assert '<option value="IMMEDIATE" selected>' in response.body.decode("utf8")

    def test_another_code(self, app):
        subscription = Subscription(
            email="bob@example.com",
            frequency="WEEKLY",
            skip_verification=True,
        )
        code = email_auth.create_code("someone_else@example.com")

        response = app.post(
            "/subscribe/update",
            params={"code": code, "id": subscription["id"], "frequency": "daily"},
            status=302,
        )
        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUnsubscribe(object):
    def test_basic(self, app):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset["id"],
            email="bob@example.com",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": code, "dataset": dataset["id"]},
            status=302,
        )

        assert (
            response.location
            == f"http://test.ckan.net/dataset/{dataset['name']}?__no_cache__=True"
        )

    def test_group(self, app):
        group = Group()
        Subscription(
            group_id=group["id"],
            email="bob@example.com",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": code, "group": group["id"]},
            status=302,
        )

        assert (
            response.location
            == f"http://test.ckan.net/group/{group['name']}?__no_cache__=True"
        )

    def test_org(self, app):
        org = Organization()
        Subscription(
            organization_id=org["id"],
            email="bob@example.com",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": code, "organization": org["id"]},
            status=302,
        )

        assert (
            response.location
            == f"http://test.ckan.net/organization/{org['name']}?__no_cache__=True"
        )

    def test_no_code(self, app):
        dataset = Dataset()
        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": "", "dataset": dataset["id"]},
            status=302,
        )

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )

    def test_bad_code(self, app):
        dataset = Dataset()
        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": "bad-code", "dataset": dataset["id"]},
            status=302,
        )

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )

    def test_no_subscription(self, app):
        dataset = Dataset()
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe",
            params={"code": code, "dataset": dataset["id"]},
            status=302,
        )

        assert response.location.startswith(
            f"http://test.ckan.net/dataset/{dataset['name']}"
        )
        response = response.follow()
        assert (
            "Error unsubscribing: That user is not subscribed to that object"
            in response.body.decode("utf8")
        )

    def test_no_object(self, app):
        code = email_auth.create_code("bob@example.com")
        response = app.get(
            "/subscribe/unsubscribe", params={"code": code, "dataset": ""}, status=302
        )

        assert response.location == "http://test.ckan.net/?__no_cache__=True"


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestUnsubscribeAll(object):
    def test_basic(self, app):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset["id"],
            email="bob@example.com",
            skip_verification=True,
        )
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe-all", params={"code": code}, status=302
        )

        assert response.location == "http://test.ckan.net/?__no_cache__=True"
        response = response.follow()
        assert (
            "You are no longer subscribed to notifications from CKAN"
            in response.body.decode("utf8")
        )

    def test_no_code(self, app):
        response = app.get(
            "/subscribe/unsubscribe-all", params={"code": ""}, status=302
        )

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )

    def test_bad_code(self, app):
        response = app.get(
            "/subscribe/unsubscribe-all", params={"code": "bad-code"}, status=302
        )

        assert response.location.startswith(
            "http://test.ckan.net/subscribe/request_manage_code"
        )

    def test_no_subscription(self, app):
        Dataset()
        code = email_auth.create_code("bob@example.com")

        response = app.get(
            "/subscribe/unsubscribe-all", params={"code": code}, status=302
        )

        assert response.location.startswith("http://test.ckan.net/")
        response = response.follow()
        assert (
            "Error unsubscribing: That user has no subscriptions"
            in response.body.decode("utf8")
        )

    def test_no_object(self, app):
        code = email_auth.create_code("bob@example.com")
        response = app.get(
            "/subscribe/unsubscribe", params={"code": code, "dataset": ""}, status=302
        )

        assert response.location == "http://test.ckan.net/?__no_cache__=True"


@pytest.mark.ckan_config("ckan.plugins", "subscribe")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRequestManageCode(object):
    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_basic(self, mail_recipient, app):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset["id"],
            email="bob@example.com",
            skip_verification=True,
        )

        response = app.get("/subscribe/request_manage_code")
        form = response.forms["request-manage-code-form"]
        form["email"] = "bob@example.com"

        response = app.post("/subscribe/request_manage_code", data=form, headers={})

        mail_recipient.assert_called_once()
        assert response.request.path == "/"

    def test_no_email(self, app):
        app.post("/subscribe/request_manage_code", params={"email": ""}, status=200)
        # user is simply asked for the email

    def test_malformed_email(self, app):
        response = app.post(
            "/subscribe/request_manage_code",
            params={"email": "malformed-email"},
            status=200,
        )

        assert "Email malformed-email is not a valid format" in response.body.decode(
            "utf8"
        )

    def test_unknown_email(self, app):
        response = app.post(
            "/subscribe/request_manage_code",
            params={"email": "unknown@example.com"},
            status=200,
        )

        assert (
            "That email address does not have any subscriptions"
            in response.body.decode("utf8")
        )
