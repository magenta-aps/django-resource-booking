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

    EmailTemplate.NOTIFY_ALL__BOOKING_COMPLETE: 'booking_planned',
    EmailTemplate.NOTIFY_ALL__BOOKING_CANCELED: 'booking_cancelled',
    EmailTemplate.NOTITY_ALL__BOOKING_REMINDER: 'reminder',
}


def import_all():
    django.setup()

    for key, basefname in IMPORT_MAP.iteritems():
        fname = os.path.join(DIR, basefname + ".html")
        fname2 = os.path.join(DIR, basefname + "_subject.txt")

        subject = _(u"Besked fra foKUs")
        body = ''

        if os.path.exists(fname2):
            subject = open(fname2).read().strip()

        if os.path.exists(fname):
            body = open(fname).read()

        try:
            template = EmailTemplate.objects.get(key=key, unit__isnull=True)
        except EmailTemplate.DoesNotExist:
            template = EmailTemplate(key=key, unit=None)

        template.subject = subject
        template.body = body
        template.save()
