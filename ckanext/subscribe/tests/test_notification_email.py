import datetime

import ckan.tests.factories as ckan_factories
import mock
import pytest
from ckan import model
from ckan.lib.helpers import literal

from ckanext.activity.model import activity as model_activity
from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.notification import dictize_notifications
from ckanext.subscribe.notification_email import (
    dataset_href_from_activity,
    dataset_link_from_activity,
    get_notification_email_vars,
    send_notification_email,
)
from ckanext.subscribe.tests import factories
from ckanext.subscribe.utils import get_notification_email_contents


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSendNotificationEmail(object):
    @mock.patch("ckanext.subscribe.mailer.mail_recipient")
    def test_basic(self, mail_recipient):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True,
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset["id"], return_object=True): [
                activity
            ]
        }
        notifications = dictize_notifications(subscription_activities)

        send_notification_email(
            code="the-code", email="bob@example.com", notifications=notifications
        )

        mail_recipient.assert_called_once()
        body = mail_recipient.call_args[1]["body"]
        print(body)
        assert dataset["title"] in body
        assert f"http://test.ckan.net/dataset/{dataset['id']}" in body
        assert "new dataset" in body
        body = mail_recipient.call_args[1]["body_html"]
        print(body)
        assert dataset["title"] in body
        assert f"http://test.ckan.net/dataset/{dataset['id']}" in body
        assert "new dataset" in body


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetNotificationEmailContents(object):
    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True,
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset["id"], return_object=True): [
                activity
            ]
        }
        notifications = dictize_notifications(subscription_activities)
        email_vars = get_notification_email_vars(
            code="the-code", email="bob@example.com", notifications=notifications
        )
        get_notification_email_contents(email_vars)

        # just check there are no exceptions

    def test_org(self):
        org = ckan_factories.Organization()
        subscribe_model.Subscribe.set_emails_last_sent(
            subscribe_model.Frequency.IMMEDIATE.value, datetime.datetime.now()
        )
        dataset = ckan_factories.Dataset(owner_org=org["id"])
        activity = (
            model.Session.query(model_activity.Activity)
            .filter_by(object_id=dataset["id"])
            .first()
        )
        subscription_activities = {
            factories.Subscription(organization_id=org["id"], return_object=True): [
                activity
            ]
        }
        notifications = dictize_notifications(subscription_activities)
        email_vars = get_notification_email_vars(
            code="the-code", email="bob@example.com", notifications=notifications
        )
        email = get_notification_email_contents(email_vars)
        # Check we link to the dataset, not just the org
        assert f"http://test.ckan.net/dataset/{dataset['name']}" in email[1]
        assert (
            f"<a href=\"http://test.ckan.net/dataset/{dataset['name']}\">"
            f"Test Dataset</a>" in email[2],
        )


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestGetNotificationEmailVars(object):
    def test_basic(self):
        dataset, activity = factories.DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True,
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(dataset_id=dataset["id"], return_object=True): [
                activity
            ]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            code="the-code", email="bob@example.com", notifications=notifications
        )

        assert (
            email_vars["notifications"]
            == [
                {
                    "activities": [
                        {
                            "activity_type": "new dataset",
                            "dataset_id": dataset["id"],
                            "dataset_href": f"http://test.ckan.net/dataset/{dataset['name']}",
                            "dataset_link": literal(
                                f"<a href=\"http://test.ckan.net/dataset/{dataset['name']}\">{dataset['title']}</a>"
                            ),
                            "timestamp": activity.timestamp,
                        }
                    ],
                    "object_link": f"http://test.ckan.net/dataset/{dataset['id']}",
                    "object_name": dataset["name"],
                    "object_title": dataset["title"],
                    "object_type": "dataset",
                }
            ],
        )

    def test_group(self):
        group, activity = factories.GroupActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True,
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(group_id=group["id"], return_object=True): [activity]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            code="the-code", email="bob@example.com", notifications=notifications
        )

        assert (
            email_vars["notifications"]
            == [
                {
                    "activities": [
                        {
                            "activity_type": "new group",
                            "dataset_id": group["id"],
                            "dataset_href": "",
                            "dataset_link": "",
                            "timestamp": activity.timestamp,
                        }
                    ],
                    "object_link": f"http://test.ckan.net/group/{group['id']}",
                    "object_name": group["name"],
                    "object_title": group["title"],
                    "object_type": "group",
                }
            ],
        )

    def test_org(self):
        org, activity = factories.OrganizationActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10),
            return_activity=True,
        )
        # {subscription: [activity, ...], ...}
        subscription_activities = {
            factories.Subscription(organization_id=org["id"], return_object=True): [
                activity
            ]
        }
        notifications = dictize_notifications(subscription_activities)

        email_vars = get_notification_email_vars(
            code="the-code", email="bob@example.com", notifications=notifications
        )

        assert (
            email_vars["notifications"]
            == [
                {
                    "activities": [
                        {
                            "activity_type": "new organization",
                            "dataset_id": org["id"],
                            "dataset_href": "",
                            "dataset_link": "",
                            "timestamp": activity.timestamp,
                        }
                    ],
                    "object_link": f"http://test.ckan.net/organization/{org['id']}",
                    "object_name": org["name"],
                    "object_title": org["title"],
                    "object_type": "organization",
                }
            ],
        )


# sample "changed package" activity for ckan 2.8
CHANGED_PACKAGE_ACTIVITY = {
    "activity_type": "changed package",
    "data": {
        "actor": "admin",
        "package": {
            "author": "",
            "author_email": "",
            "creator_user_id": "6bf6ca45-66c1-48c3-92ae-606dbfd74f3e",
            "extras": [],
            "groups": [],
            "id": "80b00ff0-f755-4ce9-9046-938895722da4",
            "isopen": True,
            "license_id": "cc-by",
            "license_title": "Creative Commons Attribution",
            "license_url": "http://www.opendefinition.org/licenses/cc-by",
            "maintainer": "",
            "maintainer_email": "",
            "metadata_created": "2018-01-02T16:29:09.354482",
            "metadata_modified": "2018-01-02T16:29:44.834676",
            "name": "stream",
            "notes": "",
            "num_resources": 2,
            "num_tags": 0,
            "organization": {
                "approval_status": "approved",
                "created": "2017-07-21T10:47:30.290814",
                "description": "",
                "id": "a2be163e-c3c0-43c0-b361-0752f6d3aa6b",
                "image_url": "",
                "is_organization": True,
                "name": "cabinet-office",
                "revision_id": "1512649a-f1ca-463b-a72a-2d1959487435",
                "state": "active",
                "title": "Cabinet Office",
                "type": "organization",
            },
            "owner_org": "a2be163e-c3c0-43c0-b361-0752f6d3aa6b",
            "private": False,
            "relationships_as_object": [],
            "relationships_as_subject": [],
            "resources": [],
            "revision_id": "0defca72-c81d-4f62-a4a1-9fadaa089604",
            "state": "active",
            "tags": [],
            "title": "Stream",
            "type": "dataset",
            "url": "",
            "version": "",
        },
    },
    "id": "79a31a90-16ef-425c-8c38-c76a50f518ea",
    "object_id": "2faae9f6-80e2-4dba-8894-0d81503ae452",
    "revision_id": "f32cdd68-9e55-4fed-8c57-b088b895c49c",
    "timestamp": "2017-11-17T17:37:46.328411",
    "user_id": "1112c36a-4280-4cd0-81bc-5c82f1d52bdd",
}

CUSTOM_ACTIVITY = {
    "user_id": "user-id",
    "object_id": "dataset-id",
    "activity_type": "changed datastore",
    "data": {
        "resource_id": "resource-id",
        "pkg_type": "dataset-type",
        "resource_name": "june-2018",
        "owner_org": "organization-id",
        "count": 5,
    },
}


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestDatasetLinkFromActivity(object):
    def test_basic(self):
        assert (
            dataset_link_from_activity(CHANGED_PACKAGE_ACTIVITY)
            == literal('<a href="http://test.ckan.net/dataset/stream">Stream</a>'),
        )

    def test_custom_activity(self):
        # don't want an exception
        assert dataset_link_from_activity(CUSTOM_ACTIVITY) == literal("")


@pytest.mark.ckan_config("ckan.plugins", "subscribe activity")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestDatasetHrefFromActivity(object):
    def test_basic(self):
        assert (
            dataset_href_from_activity(CHANGED_PACKAGE_ACTIVITY)
            == "http://test.ckan.net/dataset/stream",
        )
