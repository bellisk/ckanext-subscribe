import datetime
import logging
from enum import Enum

from ckan import model
from ckan.model.domain_object import DomainObject
from ckan.model.meta import Session, mapper, metadata
from ckan.model.types import make_uuid
from ckan.plugins.toolkit import BaseModel
from sqlalchemy import Column, types

log = logging.getLogger(__name__)


class _DomainObject(DomainObject):
    """Convenience methods for searching objects"""

    key_attr = "id"

    @classmethod
    def get(cls, key, default=None, attr=None):
        """Finds a single entity in the register."""
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
        return self.__repr__().encode("ascii", "ignore")


class Subscription(_DomainObject, BaseModel):
    """A subscription is a record of a user saying they want to get
    notifications about a particular domain object.
    """

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

    __tablename__ = "subscription"

    id = Column("id", types.UnicodeText, primary_key=True, default=make_uuid)
    email = Column("email", types.UnicodeText, nullable=False)
    # object_type is: dataset, group or organization
    object_type = Column("object_type", types.UnicodeText, nullable=False)
    object_id = Column("object_id", types.UnicodeText, nullable=False)
    verified = Column("verified", types.Boolean, default=False)
    verification_code = Column("verification_code", types.UnicodeText)
    verification_code_expires = Column("verification_code_expires", types.DateTime)
    created = Column("created", types.DateTime, default=datetime.datetime.utcnow)
    # frequency is: immediate, daily, weekly
    frequency = Column("frequency", types.Integer)

    def __repr__(self):
        return (
            f"<Subscription id={self.id} email={self.email} "
            f"object_type={self.object_type} verified={self.verified} "
            f"frequency={Frequency(self.frequency).name}>"
        )


class Frequency(Enum):
    IMMEDIATE = 1
    DAILY = 2
    WEEKLY = 3


class LoginCode(_DomainObject, BaseModel):
    """A login code is sent out in an email to let the user click to login
    without password. A user can have multiple codes at once - new ones don't
    invalidate or overwrite each other (to avoid confusion, acknowledging this
    is at the expense of some security).
    """

    __tablename__ = "subscribe_login_code"

    id = Column("id", types.UnicodeText, primary_key=True, default=make_uuid)
    email = Column("email", types.UnicodeText, nullable=False)
    code = Column("code", types.UnicodeText, nullable=False)
    expires = Column("expires", types.DateTime)

    def __repr__(self):
        return (
            f"<LoginCode id={self.id} email={self.email} "
            f"code={self.code[:4]}... expires={self.expires}>"
        )

    @classmethod
    def validate_code(cls, code):
        if not code:
            raise ValueError("No code supplied")
        login_code = model.Session.query(cls).filter_by(code=code).first()
        if not login_code:
            raise ValueError("Code not recognized")
        if datetime.datetime.now() > login_code.expires:
            raise ValueError("Code expired")
        return login_code


class Subscribe(_DomainObject, BaseModel):
    """General state"""

    __tablename__ = "subscribe"

    id = Column("id", types.UnicodeText, primary_key=True, default=make_uuid)
    frequency = Column("frequency", types.Integer)
    emails_last_sent = Column("emails_last_sent", types.DateTime, nullable=False)

    def __repr__(self):
        return f"<Subscribe email_last_sent={self.email_last_sent}>"

    @classmethod
    def set_emails_last_sent(cls, frequency, emails_last_sent):
        subscribe = model.Session.query(cls).filter_by(frequency=frequency).first()
        if subscribe:
            subscribe.emails_last_sent = emails_last_sent
        else:
            subscribe = cls(frequency=frequency, emails_last_sent=emails_last_sent)
            model.Session.add(subscribe)
        # caller needs to do:
        #   model.Session.commit()

    @classmethod
    def get_emails_last_sent(cls, frequency):
        try:
            return (
                model.Session.query(cls)
                .filter_by(frequency=frequency)
                .first()
                .emails_last_sent
            )
        except AttributeError:
            return None
