import datetime
from collections import defaultdict

from ckan import model
from ckan.model import Package, Group, Member
from ckan.lib.dictization import model_dictize
import ckan.plugins.toolkit as toolkit
from ckan import plugins as p
from ckan.lib.email_notifications import string_to_timedelta

from ckanext.subscribe.interfaces import ISubscribe
from ckanext.subscribe import dictization
from ckanext.subscribe.model import (
    Subscription,
    Subscribe,
    Frequency,
)
from ckanext.subscribe import notification_email
from ckanext.subscribe import email_auth

log = __import__('logging').getLogger(__name__)

_config = {}


def get_config(key):
    global _config
    if not _config:
        _config['email_notifications_since'] = string_to_timedelta(
            toolkit.config.get(
                'ckan.email_notifications_since', '2 days')
        )
        _config['weekly_notification_day'] = \
            {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
             'friday': 4, 'saturday': 5, 'sunday': 6}[
                 toolkit.config.get(
                     'ckanext.subscribe.weekly_notification_day', 'friday')]
        _config['daily_and_weekly_notification_time'] = \
            datetime.datetime.strptime(
                toolkit.config.get('daily_and_weekly_notification_time',
                                   '9:00'),
                '%H:%M')

    return _config[key]


def send_any_immediate_notifications():
    log.debug('send_any_immediate_notifications')
    notification_datetime = datetime.datetime.now()
    notifications_by_email = get_immediate_notifications(notification_datetime)
    if not notifications_by_email:
        log.debug('no emails to send (immediate frequency)')
    else:
        log.debug('sending {} emails (immediate frequency)'
                  .format(len(notifications_by_email)))
        send_emails(notifications_by_email)

    # record that notifications are 'all done' up to this time
    Subscribe.set_emails_last_sent(frequency=Frequency.IMMEDIATE.value,
                                   emails_last_sent=notification_datetime)
    model.Session.commit()


def send_weekly_notifications_if_its_time_to():
    if not is_it_time_to_send_weekly_notifications():
        return

    log.debug('send_weekly_notifications')
    notification_datetime = datetime.datetime.now()
    notifications_by_email = get_weekly_notifications(notification_datetime)
    if not notifications_by_email:
        log.debug('no emails to send (weekly frequency)')
    else:
        log.debug('sending {} emails (weekly frequency)'
                  .format(len(notifications_by_email)))
        send_emails(notifications_by_email)

    # record that notifications are 'all done' up to this time
    Subscribe.set_emails_last_sent(frequency=Frequency.WEEKLY.value,
                                   emails_last_sent=notification_datetime)
    model.Session.commit()


def send_daily_notifications_if_its_time_to():
    if not is_it_time_to_send_daily_notifications():
        return

    log.debug('send_daily_notifications')
    notification_datetime = datetime.datetime.now()
    notifications_by_email = get_daily_notifications(notification_datetime)
    if not notifications_by_email:
        log.debug('no emails to send (daily frequency)')
    else:
        log.debug('sending {} emails (daily frequency)'
                  .format(len(notifications_by_email)))
        send_emails(notifications_by_email)

    # record that notifications are 'all done' up to this time
    Subscribe.set_emails_last_sent(frequency=Frequency.DAILY.value,
                                   emails_last_sent=notification_datetime)
    model.Session.commit()


def get_immediate_notifications(notification_datetime=None):
    '''Work out what immediate notifications need sending out, based on
    activity, subscriptions and past notifications.
    '''
    # just interested in activity which is recent and has a subscriber
    subscription_frequency = Frequency.IMMEDIATE.value

    # {object_id: [subscriptions]}
    objects_subscribed_to = get_objects_subscribed_to(subscription_frequency)
    if not objects_subscribed_to:
        return {}

    emails_last_sent = Subscribe.get_emails_last_sent(
        frequency=Frequency.IMMEDIATE.value)
    now = notification_datetime or datetime.datetime.now()
    catch_up_period = get_config('email_notifications_since')
    if emails_last_sent:
        include_activity_from = max(
            emails_last_sent, (now - catch_up_period))
    else:
        include_activity_from = (now - catch_up_period)

    activities = get_subscribed_to_activities(
        include_activity_from,
        objects_subscribed_to.keys()
    )
    if not activities:
        return {}
    return get_notifications_by_email(activities,
                                      objects_subscribed_to,
                                      subscription_frequency)


def get_objects_subscribed_to(subscription_frequency):
    ''' Returns the objects we're listening for activity to, and the
    subscriptions they are related to

    :returns: {object_id: [subscriptions]}
    '''
    objects_subscribed_to = defaultdict(list)  # {object_id: [subscriptions]}
    # direct subscriptions - i.e. datasets, orgs & groups
    for subscription in model.Session.query(Subscription) \
            .filter(Subscription.verified.is_(True)) \
            .filter(Subscription.frequency == subscription_frequency).all():
        objects_subscribed_to[subscription.object_id].append(subscription)
    # also include the datasets attached to the subscribed orgs
    for subscription, package_id in model.Session.query(Subscription, Package.id) \
            .filter(Subscription.verified.is_(True)) \
            .filter(Subscription.frequency == subscription_frequency) \
            .join(Group, Group.id == Subscription.object_id) \
            .filter(Group.state == 'active') \
            .filter(Group.is_organization.is_(True)) \
            .join(Package, Package.owner_org == Group.id) \
            .all():
        objects_subscribed_to[package_id].append(subscription)
    # also include the datasets attached to the subscribed orgs
    for subscription, package_id in model.Session.query(Subscription, Package.id) \
            .filter(Subscription.verified.is_(True)) \
            .filter(Subscription.frequency == subscription_frequency) \
            .join(Group, Group.id == Subscription.object_id) \
            .filter(Group.state == 'active') \
            .filter(Group.is_organization.is_(False)) \
            .join(Member, Member.group_id == Group.id) \
            .filter(Member.state == 'active') \
            .join(Package, Package.id == Member.table_id) \
            .all():
        objects_subscribed_to[package_id].append(subscription)
    return objects_subscribed_to


def is_it_time_to_send_weekly_notifications():
    emails_last_sent = Subscribe.get_emails_last_sent(
        frequency=Frequency.WEEKLY.value)
    if not emails_last_sent:
        return True
    else:
        return most_recent_weekly_notification_datetime() > emails_last_sent


def is_it_time_to_send_daily_notifications():
    emails_last_sent = Subscribe.get_emails_last_sent(
        frequency=Frequency.DAILY.value)
    if not emails_last_sent:
        return True
    else:
        return most_recent_daily_notification_datetime() > emails_last_sent


def most_recent_weekly_notification_datetime(now=None):
    now = now or datetime.datetime.now()
    this_weeks_notification_date = now + datetime.timedelta(
        days=get_config('weekly_notification_day') - now.weekday(),
        hours=get_config('daily_and_weekly_notification_time').hour - now.hour,
        minutes=get_config('daily_and_weekly_notification_time').minute - now.minute)
    if this_weeks_notification_date > now:
        return this_weeks_notification_date - datetime.timedelta(days=7)
    else:
        return this_weeks_notification_date


def most_recent_daily_notification_datetime(now=None):
    now = now or datetime.datetime.now()
    todays_notification_time = now + datetime.timedelta(
        hours=get_config('daily_and_weekly_notification_time').hour - now.hour,
        minutes=get_config('daily_and_weekly_notification_time').minute - now.minute)
    if todays_notification_time > now:
        return todays_notification_time - datetime.timedelta(days=1)
    else:
        return todays_notification_time


def get_weekly_notifications(notification_datetime=None):
    '''Work out what weekly notifications need sending out, based on activity,
    subscriptions and past notifications.
    '''
    # interested in activity which is this week and has a subscriber
    subscription_frequency = Frequency.WEEKLY.value

    # {object_id: [subsciptions]}
    objects_subscribed_to = get_objects_subscribed_to(subscription_frequency)
    if not objects_subscribed_to:
        return {}

    emails_last_sent = Subscribe.get_emails_last_sent(
        frequency=Frequency.WEEKLY.value)
    now = notification_datetime or datetime.datetime.now()
    catch_up_period = get_config('email_notifications_since')
    week = datetime.timedelta(days=7)
    if emails_last_sent:
        include_activity_from = max(
            emails_last_sent, (now - week - catch_up_period))
    else:
        include_activity_from = (now - week)

    activities = get_subscribed_to_activities(
        include_activity_from,
        objects_subscribed_to.keys()
    )
    if not activities:
        return {}
    return get_notifications_by_email(activities,
                                      objects_subscribed_to,
                                      subscription_frequency)


def get_daily_notifications(notification_datetime=None):
    '''Work out what daily notifications need sending out, based on activity,
    subscriptions and past notifications.
    '''
    # interested in activity which is this week and has a subscriber
    subscription_frequency = Frequency.DAILY.value

    # {object_id: [subscriptions]}
    objects_subscribed_to = get_objects_subscribed_to(subscription_frequency)
    if not objects_subscribed_to:
        return {}

    emails_last_sent = Subscribe.get_emails_last_sent(
        frequency=Frequency.DAILY.value)
    now = notification_datetime or datetime.datetime.now()
    catch_up_period = get_config('email_notifications_since')
    day = datetime.timedelta(days=1)
    if emails_last_sent:
        include_activity_from = max(
            emails_last_sent, (now - day - catch_up_period))
    else:
        include_activity_from = (now - day)
    activities = get_subscribed_to_activities(
        include_activity_from,
        objects_subscribed_to.keys()
    )
    if not activities:
        return {}
    return get_notifications_by_email(activities,
                                      objects_subscribed_to,
                                      subscription_frequency)


def get_subscribed_to_activities(
    include_activity_from,
    objects_subscribed_to_keys
):
    activities = []
    for subscribe_interface_implementaion in p.PluginImplementations(ISubscribe):
        activities = \
            subscribe_interface_implementaion.get_activities(
                include_activity_from, objects_subscribed_to_keys)
    return activities


def get_notifications_by_email(activities, objects_subscribed_to,
                               subscription_frequency):
    # group by email address
    # so we can send each email address one email with all their notifications
    # and also have access to the subscription object with the object_type etc
    # (done in a loop rather than sql merely because of ease/clarity)
    # email: {subscription: [activity, ...], ...}
    notifications = defaultdict(lambda: defaultdict(list))
    for activity in activities:
        for subscription in objects_subscribed_to[activity.object_id]:
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
