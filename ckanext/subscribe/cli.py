import sys
import logging

import ckan.lib.cli as cli
import ckan.plugins as p


class subscribeCommand(cli.CkanCommand):
    '''subscribe commands

    Usage:

        subscribe init
            Initialize the ckanext-subscribe's database table
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
        if self.args[0] == 'initdb':
            self._load_config()
            self._setup_subscribe_logger()
            self._initdb()
        else:
            self.parser.error('Unrecognized command')

    def _setup_subscribe_logger(self):
        # whilst the deveopment.ini's loggers are setup now, because this is
        # cli, let's ensure subscribe debug messages are printed for the user
        logger = logging.getLogger('ckanext.subscribe')
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '      %(name)-12s %(levelname)-5s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # in case the config

    def _initdb(self):
        from ckanext.subscribe.model import setup as db_setup
        db_setup()

        print('DB tables created')

    def _submit_all(self):
        # submit every package
        # for each package in the package list,
        #   submit each resource w/ _submit_package
        import ckan.model as model
        package_list = p.toolkit.get_action('package_list')(
            {'model': model, 'ignore_auth': True}, {})
        print('Processing %d datasets' % len(package_list))
        user = p.toolkit.get_action('get_site_user')(
            {'model': model, 'ignore_auth': True}, {})
        for p_id in package_list:
            self._submit_package(p_id, user, indent=2)

    def _submit_package(self, pkg_id, user=None, indent=0):
        import ckan.model as model
        if not user:
            user = p.toolkit.get_action('get_site_user')(
                {'model': model, 'ignore_auth': True}, {})

        try:
            pkg = p.toolkit.get_action('package_show')(
                {'model': model, 'ignore_auth': True},
                {'id': pkg_id.strip()})
        except Exception as e:
            print(e)
            print(' ' * indent + 'Dataset "{}" was not found'.format(pkg_id))
            sys.exit(1)

        print(' ' * indent + 'Processing dataset {} with {} resources'.format(
              pkg['name'], len(pkg['resources'])))
        for resource in pkg['resources']:
            try:
                resource['package_name'] = pkg['name']  # for debug output
                self._submit_resource(resource, user, indent=indent + 2)
            except Exception as e:
                self.error_occured = True
                print(e)
                print(' ' * indent + 'ERROR submitting resource "{}" '.format(
                    resource['id']))
                continue
