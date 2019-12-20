import logging

from sqlalchemy import Table, Column, types

from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

__all__ = [
    'Subscription', 'subscription_table',
]

subscription_table = None


def setup():

    if subscription_table is None:
        define_tables()
        log.debug('Subscription tables defined in memory')

    if not model.package_table.exists():
        log.debug('Subscription table creation deferred')
        return

    if not subscription_table.exists():

        # Create each table individually rather than
        # using metadata.create_all()
        subscription_table.create()

        log.debug('Subscription tables created')


class _DomainObject(DomainObject):
    '''Convenience methods for searching objects
    '''
    key_attr = 'id'

    @classmethod
    def get(cls, key, default=None, attr=None):
        '''Finds a single entity in the register.'''
        if attr is None:
            attr = cls.key_attr
        kwds = {attr: key}
        o = cls.filter(**kwds).first()
        if o:
            return o
        else:
            return default

    @classmethod
    def filter(cls, **kwds):
        query = Session.query(cls).autoflush(False)
        return query.filter_by(**kwds)


class Subscription(_DomainObject):
    '''A subscription is a record of a user saying they want to get
    notifications about a particular domain object.
    '''
    def __repr__(self):
        return '<Subscription id=%s title=%s url=%s active=%r>' % \
               (self.id, self.title, self.url, self.active)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')


def define_tables():

    global subscription_table

    subscription_table = Table(
        'subscription',
        metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('email', types.UnicodeText, nullable=False),
        Column('object_type', types.UnicodeText, nullable=False),
        # object_type is: dataset, group or organization
        Column('object_id', types.UnicodeText, nullable=False),
        Column('verified', types.Boolean, default=False),
        Column('verification_code', types.UnicodeText),
        Column('verification_code_expires', types.DateTime),
    )

    mapper(
        Subscription,
        subscription_table,
    )
