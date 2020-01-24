import uuid

from ckan.lib.dictization import table_dict_save, table_dictize
from ckan import model

from ckanext.subscribe.model import Subscription, Frequency


def subscription_save(subscription_dict, context):
    subscription_obj = table_dict_save(
        subscription_dict, Subscription, context)

    if not subscription_obj.id:
        subscription_obj.id = str(uuid.uuid4())

    return subscription_obj


def dictize_subscription(subscription_obj, context, include_name=False):
    subscription_dict = table_dictize(subscription_obj, context)

    # user needs to get the code from the email, to show consent, so there's no
    # exception given for admins to sign someone up on their behalf
    subscription_dict.pop('verification_code')

    if include_name:
        if subscription_dict['object_type'] == 'dataset':
            subscription_dict['object_name'] = \
                model.Package.get(subscription_dict['object_id']).id
        else:
            subscription_dict['object_name'] = \
                model.Group.get(subscription_dict['object_id']).id

    subscription_dict['frequency'] = \
        Frequency(subscription_dict['frequency']).name

    return subscription_dict
