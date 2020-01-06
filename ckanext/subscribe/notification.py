import datetime
from collections import defaultdict

from sqlalchemy import func
from rq_scheduler import Scheduler
from rq.job import Job

from ckan import model
from ckan.model import Activity
from ckan.lib.dictization import model_dictize
from ckan.lib.redis import connect_to_redis
import ckan.lib.jobs
import ckan.plugins.toolkit as toolkit

from ckanext.subscribe import dictization
from ckanext.subscribe.model import Subscription
from ckanext.subscribe import notification_email
from ckanext.subscribe import email_auth

log = __import__('logging').getLogger(__name__)
config = toolkit.config

CONTINUOUS_NOTIFICATION_GRACE_PERIOD_MINUTES = int(
    config.get('ckanext.subscribe.continuous_notification_grace_period_minutes',
        5))
CONTINUOUS_NOTIFICATION_GRACE_PERIOD_MAX_MINUTES = int(
    config.get('ckanext.subscribe.continuous_notification_grace_period_max_minutes',
        60))
CONTINUOUS_NOTIFICATION_POLL_INTERVAL_SECONDS = int(
    config.get('ckanext.subscribe.continuous_notification_poll_interval_seconds',
        60))


class SubscribeJob(Job):
    '''This is for differentiating our scheduled jobs from any not created by
    ckanext-subscribe'''
    pass


def get_queue():
    queue_name = toolkit.config.get('ckanext.subscribe.queue')
    if queue_name:
        return ckan.lib.jobs.get_queue(queue_name)
    else:
        return ckan.lib.jobs.get_queue()


def get_scheduler():
    return Scheduler(queue=get_queue(),
                     connection=connect_to_redis(),
                     job_class=SubscribeJob)


def list_schedule():
    scheduler = get_scheduler()
    count = 0
    print('Schedules:')
    for job in scheduler.get_jobs():
        print('- {}'.format(printable_schedule(job)))
        count += 1
    print('Total: {} schedules'.format(count))


def printable_schedule(job):
    return 'Enqueued: {enqueued_at}  Description: {description}  {meta}'.format(
        enqueued_at=job.enqueued_at,
        description=job.description,
        meta=job.meta,  # e.g. {'interval': 60} (s)
    )


def set_schedule():
    '''Sets up scheduled tasks which will send notification emails'''
    scheduler = get_scheduler()
    # delete existing schedules
    delete_schedule()

    created = 0
    # continuous time scheduler
    scheduler.schedule(
        scheduled_time=datetime.datetime.utcnow() +
        datetime.timedelta(seconds=30),
        func=do_continuous_notifications,
        interval=CONTINUOUS_NOTIFICATION_POLL_INTERVAL_SECONDS,
        repeat=None,  # repeat forever
    )
    # use print because cli swallows logging until ckan 2.9
    print('Notifier scheduled - continuous')
    created += 1

    # TODO daily and weekly

    print('{} schedules created'.format(created))


def delete_schedule():
    scheduler = get_scheduler()
    deleted = 0
    for job in scheduler.get_jobs():
        scheduler.cancel(job)
        deleted += 1
    # use print because cli swallows logging until ckan 2.9
    print('{} existing schedules deleted'.format(deleted))


def do_continuous_notifications():
    log.debug('do_continuous_notifications')
    notifications_by_email = get_continuous_notifications()
    if not notifications_by_email:
        log.debug('no emails to send (continuous frequency)')
        return
    log.debug('sending {} emails (continuous frequency)'
              .format(len(notifications_by_email)))
    send_emails(notifications_by_email)


# TODO make this an action function
def get_continuous_notifications():
    '''Work out what notifications need sending out, based on activity,
    subscriptions and past notifications.
    '''
    # just interested in activity which is recent and has a subscriber
    objects_subscribed_to = set(
        (r[0] for r in model.Session.query(Subscription.object_id).all())
    )
    now = datetime.datetime.now()
    grace = datetime.timedelta(minutes=CONTINUOUS_NOTIFICATION_GRACE_PERIOD_MINUTES)
    grace_max = datetime.timedelta(minutes=CONTINUOUS_NOTIFICATION_GRACE_PERIOD_MAX_MINUTES)
    poll_interval = datetime.timedelta(seconds=CONTINUOUS_NOTIFICATION_POLL_INTERVAL_SECONDS)
    object_activity_oldest_newest = model.Session.query(
        Activity.object_id, func.min(Activity.timestamp), func.max(Activity.timestamp)) \
        .filter(Activity.timestamp > (now - grace
                                      - 2 * poll_interval)) \
        .filter(Activity.object_id.in_(objects_subscribed_to)) \
        .group_by(Activity.object_id) \
        .all()

    # filter activities further by their timestamp
    objects_to_notify = []
    for object_id, oldest, newest in object_activity_oldest_newest:
        if oldest < (now - grace_max + poll_interval):
            # we've waited long enough to report the oldest activity, never
            # mind the newer activity on this object
            objects_to_notify.append(object_id)
        elif newest > (now - grace):
            # recent activity on this object - don't notify yet
            pass
        else:
            # notify by default
            objects_to_notify.append(object_id)

    # get subscriptions for these activities
    subscription_activity = model.Session.query(
        Subscription, Activity) \
        .join(Activity, Subscription.object_id == Activity.object_id) \
        .filter(Subscription.object_id.in_(objects_to_notify)) \
        .all()

    # group by email address
    # so we can send each email address one email with all their notifications
    # and also have access to the subscription object with the object_type etc
    # (done in a loop rather than sql merely because of ease/clarity)
    # email: {subscription: [activity, ...], ...}
    notifications = defaultdict(lambda: defaultdict(list))
    for subscription, activity in subscription_activity:
        notifications[subscription.email][subscription].append(activity)

    # dictize
    notifications_by_email_dictized = defaultdict(list)
    for email, subscription_activities in notifications.items():
        notifications_by_email_dictized[email] = \
            dictize_notifications(subscription_activities)

    return notifications_by_email_dictized


def dictize_notifications(subscription_activities):
    '''Dictizes a subscription and its activity objects

    :param subscription_activities: {subscription: [activity, ...], ...}

    :returns: [{'subscription': {...}, {'activities': [{...}, ...]}}]
    '''
    context = {'model': model, 'session': model.Session}
    notifications_dictized = []
    for subscription, activities in subscription_activities.items():
        subscription_dict = \
            dictization.dictize_subscription(subscription, context)
        activity_dicts = model_dictize.activity_list_dictize(
            activities, context)
        notifications_dictized.append(
            {
                'subscription': subscription_dict,
                'activities': activity_dicts,
            }
        )
    return notifications_dictized


def send_emails(notifications_by_email):
    for email, notifications in notifications_by_email.items():
        code = email_auth.create_code(email)
        notification_email.send_notification_email(code, email, notifications)
