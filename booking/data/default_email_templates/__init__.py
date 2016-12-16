# encoding: utf-8
from booking.models import EmailTemplate, EmailTemplateType
from django.utils.translation import ugettext as _
import django
import os


DIR = os.path.dirname(__file__)


IMPORT_MAP = {
    EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED: 'on_booking_to_booker',
    EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED: 'on_booking_to_booker_untimed',
    EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED: 'on_booking_to_editors',
    EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER: 'request_teacher',
    EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER: 'request_host',
    EmailTemplateType.NOTIFY_HOST__ASSOCIATED: 'host_associated_notification',
    EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED:
        'teacher_associated_notification',
    EmailTemplateType.NOTIFY_HOST__REQ_ROOM: 'request_room',
    EmailTemplateType.NOTIFY_GUEST__GENERAL_MSG: 'general_message',
    EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE: 'booking_planned',
    EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED: 'booking_cancelled',
    EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER: 'reminder',
    EmailTemplateType.NOTIFY_ALL_EVALUATION: 'evaluation',
    EmailTemplateType.NOTIFY_GUEST_REMINDER: 'reminder',
    EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE: 'no_hosts_notification',
    EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE: 'contact_mail',
    EmailTemplateType.SYSTEM__EMAIL_REPLY: 'email_reply',
    EmailTemplateType.SYSTEM__USER_CREATED: 'user_created',
    EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_WAITING: 'waitinglist_joined',
    EmailTemplateType.NOTIFY_GUEST__SPOT_OPEN: 'waitinglist_offer',
    EmailTemplateType.NOTIFY_GUEST__SPOT_ACCEPTED: 'waitinglist_accepted',
    EmailTemplateType.NOTIFY_GUEST__SPOT_REJECTED: 'waitinglist_rejected',
    EmailTemplateType.NOTIFY_EDITORS__SPOT_REJECTED:
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
        template = EmailTemplate.objects.get(
            key=key, organizationalunit__isnull=True
        )
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
