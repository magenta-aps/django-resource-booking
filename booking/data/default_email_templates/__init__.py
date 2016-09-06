# encoding: utf-8
from booking.models import EmailTemplate
from django.utils.translation import ugettext as _
import django
import os


DIR = os.path.dirname(__file__)


IMPORT_MAP = {
    EmailTemplate.NOTIFY_GUEST__BOOKING_CREATED: 'on_booking_to_booker',
    EmailTemplate.NOTIFY_EDITORS__BOOKING_CREATED: 'on_booking_to_editors',
    EmailTemplate.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER: 'request_teacher',
    EmailTemplate.NOTIFY_HOST__REQ_HOST_VOLUNTEER: 'request_host',
    EmailTemplate.NOTIFY_HOST__ASSOCIATED: 'host_associated_notification',
    EmailTemplate.NOTIFY_TEACHER__ASSOCIATED:
        'teacher_associated_notification',
    EmailTemplate.NOTIFY_HOST__REQ_ROOM: 'request_room',
    EmailTemplate.NOTIFY_GUEST__GENERAL_MSG: 'general_message',
    EmailTemplate.NOTIFY_ALL__BOOKING_COMPLETE: 'booking_planned',
    EmailTemplate.NOTIFY_ALL__BOOKING_CANCELED: 'booking_cancelled',
    EmailTemplate.NOTITY_ALL__BOOKING_REMINDER: 'reminder',
    EmailTemplate.NOTIFY_ALL_EVALUATION: 'evaluation',
    EmailTemplate.NOTIFY_GUEST_REMINDER: 'reminder',
    EmailTemplate.NOTIFY_HOST__HOSTROLE_IDLE: 'no_hosts_notification',
    EmailTemplate.SYSTEM__BASICMAIL_ENVELOPE: 'contact_mail',
    EmailTemplate.SYSTEM__EMAIL_REPLY: 'email_reply',
    EmailTemplate.SYSTEM__USER_CREATED: 'user_created',
    EmailTemplate.NOTIFY_GUEST__BOOKING_CREATED_WAITING: 'waitinglist_joined',
    EmailTemplate.NOTIFY_GUEST__SPOT_OPEN: 'waitinglist_offer',
    EmailTemplate.NOTIFY_GUEST__SPOT_ACCEPTED: 'waitinglist_accepted',
    EmailTemplate.NOTIFY_GUEST__SPOT_REJECTED: 'waitinglist_rejected',
    EmailTemplate.NOTIFY_EDITORS__SPOT_REJECTED:
        'waitinglist_rejected_coordinator'
}


def import_one(key):
    basefname = IMPORT_MAP[key]

    fname = os.path.join(DIR, basefname + ".html")
    fname2 = os.path.join(DIR, basefname + "_subject.txt")

    subject = _(u"Besked fra foKUs")
    body = ''

    if os.path.exists(fname2):
        subject = open(fname2).read().strip()

    if os.path.exists(fname):
        body = open(fname).read()

    try:
        template = EmailTemplate.objects.get(key=key, organizationalunit__isnull=True)
    except EmailTemplate.DoesNotExist:
        template = EmailTemplate(key=key, organizationalunit=None)

    template.subject = subject
    template.body = body
    template.save()


def import_all():
    django.setup()

    for key in IMPORT_MAP:
        import_one(key)


def export_one(key):
    basefname = IMPORT_MAP[key]

    fname = os.path.join(DIR, basefname + ".html")
    fname2 = os.path.join(DIR, basefname + "_subject.txt")

    try:
        template = EmailTemplate.objects.get(key=key, organizationalunit__isnull=True)
    except EmailTemplate.DoesNotExist:
        print("Template not found!")

    subject = template.subject
    body = template.body

    if os.path.exists(fname2):
        with open(fname2, 'w+') as subject_file:
            try:
                subject_file.write(subject.encode('utf8'))
            except os.error:
                print("Couldn't write file: %s" % fname2)
            finally:
                subject_file.close()

    if os.path.exists(fname):
        with open(fname, 'w+') as body_file:
            try:
                body_file.write(body.encode('utf8'))
            except os.error:
                print("Couldn't write file: %s" % fname)
            finally:
                body_file.close()


def export_all():
    django.setup()

    for key in IMPORT_MAP:
        export_one(key)
