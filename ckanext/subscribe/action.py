# encoding: utf-8

import logging

import ckan.plugins as p
import ckan.lib.navl.dictization_functions

from ckanext.subscribe import schema


log = logging.getLogger(__name__)
_validate = ckan.lib.navl.dictization_functions.validate
_check_access = p.toolkit.check_access
NotFound = p.toolkit.ObjectNotFound


def subscribe_signup(context, data_dict):
    '''Signup to get notifications of email

    :param email: Email address to get notifications to
    :param dataset: Dataset name or id to get notifications about
    :param group: Group or organization name or id to get notifications about
                  (specify dataset or group - not both)

    :returns: the newly created subscription
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    schema = schema.subscribe_schema()
    data, errors = _validate(data_dict, schema, context)
    _check_access(u'subscribe_signup', context, data_dict)

    data = {
        'email': email,
        'user': context['user']
    }
    if dataset:
        data['object_type'] = 'package'
        dataset_obj = model.Package.get(dataset)
        data['object_id'] = dataset_obj.id
    else:
        data['object_type'] = 'group'
        group_obj = model.Group.get(group)
        data['object_id'] = group_obj.id

    existing_subscription = model.Session.query(Subscription)
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