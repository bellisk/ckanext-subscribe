import sys
import datetime

import ckan.lib.cli as cli
import ckan.plugins as p


class subscribeCommand(cli.CkanCommand):
    '''subscribe commands

    Usage:

        subscribe init
            Initialize the ckanext-subscribe's database table and schedule

        subscribe initdb
            Initialize the the ckanext-subscribe's database table

        subscribe schedule
            Show the ckanext-subscribe's schedule

        subscribe schedule init
            Initialize the ckanext-subscribe's schedule

        subscribe schedule delete
            Delete the ckanext-subscribe's schedule

        subscribe create-test-activity {package-name|group-name|org-name}
            Create some activity for testing purposes, for a given existing
            object.

        subscribe delete-test-activity
            Delete any test activity (i.e. clean up after doing
            'create-test-activity'). Works for test activity on all objects.

    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 1

    def __init__(self, name):
        super(subscribeCommand, self).__init__(name)

    def command(self):
        if not self.args:
            print(self.usage)
            sys.exit(1)
        if self.args[0] == 'init':
            self._load_config()
            self._initdb()
            print('--')
            self._subscribe_init()
        elif self.args[0] == 'initdb':
            self._load_config()
            self._initdb()
        elif self.args[0] == 'schedule':
            args = self.args[1:]
            if not args:
                self._load_config()
                self._initdb()
                self._subscribe_list()
            elif args[0] == 'init':
                self._load_config()
                self._subscribe_init()
            elif args[0] == 'delete':
                self._load_config()
                self._subscribe_delete()
            else:
                self.parser.error('Unrecognized schedule sub-command')
        elif self.args[0] == 'create-test-activity':
            self._load_config()
            object_id = self.args[1]
            self._create_test_activity(object_id)
        elif self.args[0] == 'delete-test-activity':
            self._load_config()
            self._delete_test_activity()
        else:
            self.parser.error('Unrecognized command')

    def _initdb(self):
        from ckanext.subscribe.model import setup as db_setup
        db_setup()

        print('DB tables created')

    def _subscribe_list(self):
        from ckanext.subscribe import notification
        notification.list_schedule()

    def _subscribe_init(self):
        from ckanext.subscribe import notification
        notification.set_schedule()
        notification.list_schedule()

    def _subscribe_delete(self):
        from ckanext.subscribe import notification
        notification.delete_schedule()

    def _create_test_activity(self, object_id):
        from ckan import model
        from ckanext.subscribe import notification
        if p.toolkit.check_ckan_version(max_version='2.8.99'):
            model.repo.new_revision()
        obj = model.Package.get(object_id) or model.Group.get(object_id)
        assert obj, 'Object could not be found'
        grace = datetime.timedelta(
            minutes=notification.CONTINUOUS_NOTIFICATION_GRACE_PERIOD_MINUTES)
        site_user = p.toolkit.get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        site_user_obj = model.User.get(site_user['name'])
        activity = model.Activity(
            user_id=site_user_obj.id,
            object_id=obj.id,
            activity_type='test activity',
            revision_id=None,
        )
        # put it slightly in the past, so it notifies immediately
        activity.timestamp = datetime.datetime.now() - grace
        model.Session.add(activity)
        print(activity)
        model.Session.commit()

    def _delete_test_activity(self):
        from ckan import model
        test_activity = model.Session.query(model.Activity) \
            .filter_by(activity_type='test activity') \
            .all()
        model.Session.delete(test_activity)
