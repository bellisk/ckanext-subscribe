# encoding: utf-8

import factory

import ckan.plugins as p
import ckan.tests.factories as ckan_factories
from ckan import model

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

        if not (kwargs.get('dataset_id') or kwargs.get('group_id')):
            kwargs['dataset_id'] = ckan_factories.Dataset()['id']

        subscription_dict = \
            p.toolkit.get_action('subscribe_signup')(context, kwargs)

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
