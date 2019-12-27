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
    subscription_dict = table_dictize(subscription_obj, context)
    # user needs to get the code from the email, to show consent, so there's no
    # exception given for admins to sign someone up on their behalf
    subscription_dict.pop('verification_code')
    return subscription_dict
