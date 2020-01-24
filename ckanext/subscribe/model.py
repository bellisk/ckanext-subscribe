import logging
import datetime
from enum import Enum

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
login_code_table = None
subscribe_table = None


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
        login_code_table.create()
        subscribe_table.create()

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

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')


class Subscription(_DomainObject):
    '''A subscription is a record of a user saying they want to get
    notifications about a particular domain object.
    '''
    # Note on codes:
    #
    # The Subscription.code is emailed and the user clicks to signify that they
    # are willing to receive emails for a particular subscription. (They are
    # then emailed a LoginCode.code for other interactions of any of their
    # subscriptions - manage, unsubscribe etc.)
    #
    # The Subscription.code design aims to follows this OWASP guidance:
    # https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html#semantic-validation
    # Subsequent codes invalidate previous ones, although arguably this level
    # of security is not necessary for a subscription.
    #
    # The LoginCode.code does not invalidate previous ones, for convenience.

    def __repr__(self):
        return '<Subscription id={} email={} object_type={} verified={} ' \
            'frequency={}>'.format(
                self.id, self.email, self.object_type, self.verified,
                Frequency(self.frequency).name)


class Frequency(Enum):
    IMMEDIATE = 1
    DAILY = 2
    WEEKLY = 3


class LoginCode(_DomainObject):
    '''A login code is sent out in an email to let the user click to login
    without password. A user can have multiple codes at once - new ones don't
    invalidate or overwrite each other (to avoid confusion, acknowledging this
    is at the expense of some security).
    '''
    def __repr__(self):
        return '<LoginCode id={} email={} code={}... expires={}>'.format(
            self.id, self.email, self.code[:4], self.expires)

    @classmethod
    def validate_code(cls, code):
        if not code:
            raise ValueError('No code supplied')
        login_code = model.Session.query(cls) \
            .filter_by(code=code) \
            .first()
        if not login_code:
            raise ValueError('Code not recognized')
        if datetime.datetime.now() > login_code.expires:
            raise ValueError('Code expired')
        return login_code


class Subscribe(_DomainObject):
    '''General state
    '''
    def __repr__(self):
        return '<Subscribe email_last_sent={}>'.format(
            self.email_last_sent)

    @classmethod
    def set_emails_last_sent(cls, frequency, emails_last_sent):
        subscribe = model.Session.query(cls) \
            .filter_by(frequency=frequency) \
            .first()
        if subscribe:
            subscribe.emails_last_sent = emails_last_sent
        else:
            subscribe = cls(frequency=frequency,
                            emails_last_sent=emails_last_sent)
            model.Session.add(subscribe)
        # caller needs to do:
        #   model.Session.commit()

    @classmethod
    def get_emails_last_sent(cls, frequency):
        try:
            return model.Session.query(cls) \
                .filter_by(frequency=frequency) \
                .first() \
                .emails_last_sent
        except AttributeError:
            return None


def define_tables():

    global subscription_table, login_code_table, subscribe_table

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
        Column('created', types.DateTime, default=datetime.datetime.utcnow),
        # frequency is: immediate, daily, weekly
        Column('frequency', types.Integer),
    )

    login_code_table = Table(
        'subscribe_login_code',
        metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('email', types.UnicodeText, nullable=False),
        Column('code', types.UnicodeText, nullable=False),
        Column('expires', types.DateTime),
    )

    subscribe_table = Table(
        'subscribe',
        metadata,
        # just stores one row for each frequency now
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('frequency', types.Integer),
        Column('emails_last_sent', types.DateTime, nullable=False),
    )

    mapper(
        Subscription,
        subscription_table,
    )
    mapper(
        LoginCode,
        login_code_table,
    )
    mapper(
        Subscribe,
        subscribe_table,
    )
