# encoding: utf-8

import datetime

import factory

import ckan.plugins as p
import ckan.tests.factories as ckan_factories

import ckanext.subscribe.model


class Subscription(factory.Factory):
    '''A factory class for creating subscriptions.'''

    FACTORY_FOR = ckanext.subscribe.model.Subscription

        # Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        # Column('email', types.UnicodeText, nullable=False),
        # Column('object_type', types.UnicodeText, nullable=False),
        #     # object_type is: dataset, group or organization
        # Column('object_id', types.UnicodeText, nullable=False),
        # Column('verified', types.Boolean, default=False),
        # Column('verification_code', types.UnicodeText),
        # Column('verification_code_expires', types.DateTime),

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