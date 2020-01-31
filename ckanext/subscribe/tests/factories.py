# encoding: utf-8

import datetime

import factory

import ckan.plugins as p
import ckan.tests.factories as ckan_factories
from ckan import model
from ckan.lib.dictization import table_dictize
import ckan.lib.dictization.model_dictize as model_dictize

import ckanext.subscribe.model
from ckanext.subscribe import dictization


class Subscription(factory.Factory):
    '''A factory class for creating subscriptions via the subscribe_signup
    action.
    '''

    FACTORY_FOR = ckanext.subscribe.model.Subscription

    id = factory.Sequence(lambda n: 'test_sub_{n}'.format(n=n))
    email = 'bob@example.com'
    return_object = False
    created = datetime.datetime.now() - datetime.timedelta(hours=1)
    frequency = 'immediate'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        if 'skip_verification' not in kwargs:
            kwargs['skip_verification'] = True

        if not (kwargs.get('dataset_id') or kwargs.get('group_id') or
                kwargs.get('organization_id')):
            kwargs['dataset_id'] = ckan_factories.Dataset()['id']

        subscription_dict = \
            p.toolkit.get_action('subscribe_signup')(context, kwargs)

        # to set the 'created' time we need to edit the object
        subscription = \
            model.Session.query(ckanext.subscribe.model.Subscription) \
            .get(subscription_dict['id'])
        if kwargs.get('created'):
            subscription.created = kwargs['created']
            model.repo.commit()
        subscription_dict = \
            dictization.dictize_subscription(subscription, context)

        if kwargs['return_object']:
            return ckanext.subscribe.model.Subscription.get(
                subscription_dict['id'])
        return subscription_dict


class SubscriptionLowLevel(factory.Factory):
    '''A factory class for creating subscription object directly
    '''

    FACTORY_FOR = ckanext.subscribe.model.Subscription

    id = factory.Sequence(lambda n: 'test_sub_{n}'.format(n=n))
    email = 'bob@example.com'
    return_object = False

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, **kwargs):
        for key in ('skip_verification', 'dataset_id'):
            assert key not in kwargs, 'wrong syntax - use Subscription instead'

        if not kwargs.get('object_id'):
            kwargs['object_id'] = ckan_factories.Dataset()['id']
            kwargs['object_type'] = 'dataset'

        return_object = kwargs.pop('return_object')

        context = {'user': ckan_factories._get_action_user_name(kwargs),
                   'model': model,
                   'session': model.Session}

        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            model.repo.new_revision()
        subscription_obj = dictization.subscription_save(kwargs, context)
        model.repo.commit()

        if return_object:
            return subscription_obj
        subscription_dict = \
            dictization.dictize_subscription(subscription_obj, context)
        return subscription_dict


# because the core ckan one is not fully featured
class Activity(factory.Factory):
    """A factory class for creating CKAN activity objects."""

    FACTORY_FOR = model.Activity

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs),
                   'model': model}

        if not kwargs.get('user_id'):
            kwargs['user_id'] = ckan_factories.User()['id']

        activity_dict = \
            p.toolkit.get_action('activity_create')(context, kwargs)

        # to set the timestamp we need to edit the object
        activity = model.Session.query(model.Activity).get(activity_dict['id'])
        if kwargs.get('timestamp'):
            activity.timestamp = kwargs['timestamp']
            model.repo.commit()

        if kwargs.get('return_object'):
            return activity

        return model_dictize.activity_dictize(activity, context)


class DatasetActivity(factory.Factory):
    """A factory class for creating a CKAN dataset and associated activity
    object."""

    FACTORY_FOR = model.Activity

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        return_activity = kwargs.pop('return_activity') \
            if 'return_activity' in kwargs else False

        if not kwargs.get('user_id'):
            kwargs['user_id'] = ckan_factories.User()['id']

        dataset = ckan_factories.Dataset()
        # the activity object is made as a byproduct

        activity_obj = model.Session.query(model.Activity) \
            .filter_by(object_id=dataset['id']) \
            .first()

        if kwargs:
            for k, v in kwargs.items():
                setattr(activity_obj, k, v)
            model.repo.commit_and_remove()

        if return_activity:
            return dataset, activity_obj
        return dataset


class GroupActivity(factory.Factory):
    """A factory class for creating a CKAN group and associated activity
    object."""

    FACTORY_FOR = model.Activity

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        return_activity = kwargs.pop('return_activity') \
            if 'return_activity' in kwargs else False

        if not kwargs.get('user_id'):
            kwargs['user_id'] = ckan_factories.User()['id']

        group = ckan_factories.Group()
        # the activity object is made as a byproduct

        activity_obj = model.Session.query(model.Activity) \
            .filter_by(object_id=group['id']) \
            .first()

        if kwargs:
            for k, v in kwargs.items():
                setattr(activity_obj, k, v)
            model.repo.commit_and_remove()

        if return_activity:
            return group, activity_obj
        return group


class OrganizationActivity(factory.Factory):
    """A factory class for creating a CKAN org and associated activity
    object."""

    FACTORY_FOR = model.Activity

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        return_activity = kwargs.pop('return_activity') \
            if 'return_activity' in kwargs else False

        if not kwargs.get('user_id'):
            kwargs['user_id'] = ckan_factories.User()['id']

        org = ckan_factories.Organization()
        # the activity object is made as a byproduct

        activity_obj = model.Session.query(model.Activity) \
            .filter_by(object_id=org['id']) \
            .first()

        if kwargs:
            for k, v in kwargs.items():
                setattr(activity_obj, k, v)
            model.repo.commit_and_remove()

        if return_activity:
            return org, activity_obj
        return org


# 'activity_show' action
def activity_show(context, activity_obj):
    if p.toolkit.check_ckan_version(max_version='2.8.99'):
        # basic version
        activity_dict = table_dictize(activity_obj, context)
    else:
        activity_dict = p.toolkit.get_action('activity_show')(
            context, {'id': activity_obj.id})
    return activity_dict
