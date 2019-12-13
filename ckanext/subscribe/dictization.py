import uuid

from ckanext.subscribe.model import Subscription
from ckan.lib.dictization import table_dict_save, table_dictize


def subscription_save(subscription_dict, context):
    subscription_obj = table_dict_save(
        subscription_dict, Subscription, context)

    if not subscription_obj.id:
        subscription_obj.id = str(uuid.uuid4())

    return subscription_obj


def dictize_subscription(subscription_obj, context):
    return table_dictize(subscription_obj, context)
