import datetime
from collections import defaultdict

from sqlalchemy import func

from ckan import model
from ckan.model import Activity
from ckan.lib.dictization import model_dictize

from ckanext.subscribe import dictization
from ckanext.subscribe.model import Subscription

NOTIFY_WHEN_OBJECT_NOT_CHANGED_FOR = datetime.timedelta(minutes=5)
MAX_TIME_TO_WAIT_BEFORE_NOTIFYING = datetime.timedelta(minutes=60)
POLL_TIME_PERIOD = datetime.timedelta(minutes=1)


def get_notifications():
    '''Work out what notifications need sending out, based on activity,
    subscriptions and past notifications.
    '''
    # just interested in activity which is recent and has a subscriber
    objects_subscribed_to = set(
        (r[0] for r in model.Session.query(Subscription.object_id).all())
    )
    now = datetime.datetime.now()
    object_activity_oldest_newest = model.Session.query(
        Activity.object_id, func.max(Activity.timestamp), func.min(Activity.timestamp)) \
        .filter(Activity.timestamp > (now - MAX_TIME_TO_WAIT_BEFORE_NOTIFYING
                                      - 2 * POLL_TIME_PERIOD)) \
        .filter(Activity.object_id.in_(objects_subscribed_to)) \
        .group_by(Activity.object_id) \
        .all()

    # filter activities further by their timestamp
    objects_to_notify = []
    for object_id, oldest, newest in object_activity_oldest_newest:
        if oldest < (now - MAX_TIME_TO_WAIT_BEFORE_NOTIFYING
                     + POLL_TIME_PERIOD):
            # we've waited long enough to report the oldest activity, never
            # mind the newer activity on this object
            objects_to_notify.append(object_id)
        elif newest > (now - NOTIFY_WHEN_OBJECT_NOT_CHANGED_FOR):
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

    # group by subscription (email) (not done in sql merely for ease/clarity)
    notifications = defaultdict(list)  # subscription: [activity, ...]
    for subscription, activity in subscription_activity:
        notifications[subscription].append(activity)

    # dictize
    context = {'model': model, 'session': model.Session}
    notifications_dictized = []
    for subscription, activities in notifications.items():
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
