# encoding: utf-8

# For sending HTML emails. Based on core ckan's mailer

from time import time
import smtplib
import socket


from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email import utils

import ckan
import ckan.plugins as p
from ckan.lib.mailer import MailerException

log = __import__('logging').getLogger(__name__)
config = p.toolkit.config
_ = p.toolkit._
asbool = p.toolkit.asbool


def _mail_recipient(recipient_name, recipient_email,
                    sender_name, sender_url, subject,
                    body, body_html=None, headers=None):

    if not headers:
        headers = {}

    mail_from = config.get('smtp.mail_from')
    reply_to = config.get('smtp.reply_to')
    if body_html:
        # multipart
        msg = MIMEMultipart('alternative')
        part1 = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
        part2 = MIMEText(body_html.encode('utf-8'), 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
    else:
        # just plain text
        msg = MIMEText(body.encode('utf-8'), 'plain', 'utf-8')
    for k, v in headers.items():
        if k in msg.keys():
            msg.replace_header(k, v)
        else:
            msg.add_header(k, v)
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg['From'] = _("%s <%s>") % (sender_name, mail_from)
    recipient = u"%s <%s>" % (recipient_name, recipient_email)
    msg['To'] = Header(recipient, 'utf-8')
    msg['Date'] = utils.formatdate(time())
    msg['X-Mailer'] = "CKAN %s" % ckan.__version__
    if reply_to and reply_to != '':
        msg['Reply-to'] = reply_to
    _mail_payload(msg, mail_from, recipient_email)


def _mail_payload(msg, mail_from, recipient_email):
    # Send the email using Python's smtplib.
    smtp_connection = smtplib.SMTP()
    if 'smtp.test_server' in config:
        # If 'smtp.test_server' is configured we assume we're running tests,
        # and don't use the smtp.server, starttls, user, password etc. options.
        smtp_server = config['smtp.test_server']
        smtp_starttls = False
        smtp_user = None
        smtp_password = None
    else:
        smtp_server = config.get('smtp.server', 'localhost')
        smtp_starttls = asbool(
            config.get('smtp.starttls'))
        smtp_user = config.get('smtp.user')
        smtp_password = config.get('smtp.password')

    try:
        smtp_connection.connect(smtp_server)
    except socket.error as e:
        log.exception(e)
        raise MailerException('SMTP server could not be connected to: "%s" %s'
                              % (smtp_server, e))
    try:
        # Identify ourselves and prompt the server for supported features.
        smtp_connection.ehlo()

        # If 'smtp.starttls' is on in CKAN config, try to put the SMTP
        # connection into TLS mode.
        if smtp_starttls:
            if smtp_connection.has_extn('STARTTLS'):
                smtp_connection.starttls()
                # Re-identify ourselves over TLS connection.
                smtp_connection.ehlo()
            else:
                raise MailerException("SMTP server does not support STARTTLS")

        # If 'smtp.user' is in CKAN config, try to login to SMTP server.
        if smtp_user:
            assert smtp_password, ("If smtp.user is configured then "
                                   "smtp.password must be configured as well.")
            smtp_connection.login(smtp_user, smtp_password)

        smtp_connection.sendmail(mail_from, [recipient_email], msg.as_string())
        log.info("Sent email to {0}".format(recipient_email))

    except smtplib.SMTPException as e:
        msg = '%r' % e
        log.exception(msg)
        raise MailerException(msg)
    finally:
        smtp_connection.quit()


def mail_recipient(recipient_name, recipient_email, subject,
                   body, body_html=None, headers={}):
    site_title = config.get('ckan.site_title')
    site_url = config.get('ckan.site_url')
    return _mail_recipient(recipient_name, recipient_email,
                           site_title, site_url, subject, body,
                           body_html=body_html, headers=headers)
