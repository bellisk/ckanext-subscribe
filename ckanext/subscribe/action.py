# encoding: utf-8

import logging

import ckan.plugins as p
from ckan.logic import validate  # put in toolkit?

from ckanext.subscribe import schema
from ckanext.subscribe.model import Subscription


log = logging.getLogger(__name__)
_check_access = p.toolkit.check_access
NotFound = p.toolkit.ObjectNotFound


@validate(schema.subscribe_schema)
def subscribe_signup(context, data_dict):
    '''Signup to get notifications of email

    :param email: Email address to get notifications to
    :param package_id: Package name or id to get notifications about
                       (specify package_id or group_id - not both)
    :param group_id: Group or organization name or id to get notifications
                     about (specify package_id or group_id - not both)

    :returns: the newly created subscription
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    _check_access(u'subscribe_signup', context, data_dict)

    data = {
        'email': data_dict['email'],
        'user': context['user']
    }
    if data_dict.get('dataset_id'):
        data['object_type'] = 'dataset'
        dataset_obj = model.Package.get(data_dict['dataset_id'])
        data['object_id'] = dataset_obj.id
    else:
        data['object_type'] = 'group'
        group_obj = model.Group.get(data_dict['group_id'])
        data['object_id'] = group_obj.id

    # existing_subscription = model.Session.query(Subscription)
    subscription = model_save.package_dict_save(data, context)


    rev = model.repo.new_revision()
    rev.author = user


    dictized_jobs = []
    queues = data_dict.get(u'queues')
    if queues:
        queues = [jobs.get_queue(q) for q in queues]
    else:
        queues = jobs.get_all_queues()
    for queue in queues:
        for job in queue.jobs:
            dictized_jobs.append(jobs.dictize_job(job))
    return dictized_jobs