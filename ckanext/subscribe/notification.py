import datetime
from collections import defaultdict

from sqlalchemy import func

from ckan import model
from ckan.model import Activity
from ckan.lib.dictization import model_dictize
import ckan.plugins.toolkit as toolkit
from ckan.lib.email_notifications import string_to_timedelta

from ckanext.subscribe import dictization
from ckanext.subscribe.model import (
    Subscription,
    Subscribe,
)
from ckanext.subscribe import notification_email
from ckanext.subscribe import email_auth

log = __import__('logging').getLogger(__name__)

_config = {}


def get_config(key):
    global _config
    if not _config:
        _config['immediate_notification_grace_period'] = \
            datetime.timedelta(minutes=int(
                toolkit.config.get(
                    'ckanext.subscribe.immediate_notification_grace_period_minutes',
                    5)))
        _config['immediate_notification_grace_period_max'] = \
            datetime.timedelta(minutes=int(
                toolkit.config.get(
                    'ckanext.subscribe.immediate_notification_grace_period_max_minutes',
                    60)))
        _config['email_notifications_since'] = string_to_timedelta(
            toolkit.config.get(
                'ckan.email_notifications_since', '2 days')
        )
    return _config[key]


def send_any_immediate_notifications():
    log.debug('send_any_immediate_notifications')
    notification_datetime = datetime.datetime.now()
    notifications_by_email = get_immediate_notifications(notification_datetime)
    if not notifications_by_email:
        log.debug('no emails to send (immediate frequency)')
        return
    log.debug('sending {} emails (immediate frequency)'
              .format(len(notifications_by_email)))
    send_emails(notifications_by_email)

    # record that notifications are 'all done' up to this time
    Subscribe.set_emails_last_sent(notification_datetime)
    model.Session.commit()


# TODO make this an action function
def get_immediate_notifications(notification_datetime=None):
    '''Work out what notifications need sending out, based on activity,
    subscriptions and past notifications.
    '''
    # just interested in activity which is recent and has a subscriber
    objects_subscribed_to = set(
        (r[0] for r in model.Session.query(Subscription.object_id).all())
    )
    if not objects_subscribed_to:
        return {}
    try:
        emails_last_sent = Subscribe.get_emails_last_sent()
    except AttributeError:
        # some date long in the past
        emails_last_sent = \
            datetime.datetime(year=datetime.MINYEAR, month=1, day=1)
    now = notification_datetime or datetime.datetime.now()
    grace = get_config('immediate_notification_grace_period')
    grace_max = get_config('immediate_notification_grace_period_max')
    catch_up_period = get_config('email_notifications_since')
    object_activity_oldest_newest = model.Session.query(
        Activity.object_id, func.min(Activity.timestamp), func.max(Activity.timestamp)) \
        .filter(Activity.timestamp > emails_last_sent) \
        .filter(Activity.timestamp > (now - catch_up_period)) \
        .filter(Activity.object_id.in_(objects_subscribed_to)) \
        .group_by(Activity.object_id) \
        .all()

    # filter activities further by their timestamp
    objects_to_notify = []
    for object_id, oldest, newest in object_activity_oldest_newest:
        if oldest < (now - grace_max):
            # we've waited long enough to report the oldest activity, never
            # mind the newer activity on this object
            objects_to_notify.append(object_id)
        elif newest > (now - grace):
            # recent activity on this object - don't notify yet
            pass
        else:
            # notify by default
            objects_to_notify.append(object_id)
    if not objects_to_notify:
        return {}

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
        # ignore activity that occurs before this subscription was created
        if subscription.created > activity.timestamp:
            continue

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
