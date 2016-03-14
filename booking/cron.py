from datetime import timedelta, date

from booking.models import VisitOccurrenceAutosend, EmailTemplate, \
    VisitOccurrence
from django_cron import CronJobBase, Schedule


class ReminderJob(CronJobBase):
    RUN_AT_TIMES = ['01:00']

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.reminders'

    def do(self):
        print "---------------------------------------------------------------"
        print "Beginning ReminderJob (sends reminder emails)"
        autosends = list(VisitOccurrenceAutosend.objects.filter(
            enabled=True,
            template_key=EmailTemplate.NOTITY_ALL__BOOKING_REMINDER,
            days__isnull=False,
            inherit=False
        ).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitOccurrenceAutosend.objects.filter(
            inherit=True,
            template_key=EmailTemplate.NOTITY_ALL__BOOKING_REMINDER,
        ).all())

        extra = []
        for autosend in inheriting_autosends:
            inherited = autosend.get_inherited()
            if inherited.enabled and inherited.days is not None:
                autosend.days = inherited.days
                autosend.enabled = inherited.enabled
                extra.append(autosend)
        print "Found %d enabled inheriting autosends" % len(extra)
        autosends.extend(extra)

        if len(autosends) > 0:
            today = date.today()
            print "Today is: %s" % unicode(today)

            for autosend in autosends:
                if autosend is not None:
                    print "Autosend %d for VisitOccurrence %d:" % \
                        (autosend.id, autosend.visitoccurrence.id)
                    print "    VisitOccurrence starts on %s" % \
                        unicode(autosend.visitoccurrence.start_datetime.date())
                    reminderday = autosend.visitoccurrence.start_datetime.date()\
                        - timedelta(autosend.days)
                    print "    Autosend specifies to send %d days prior, on %s" % \
                        (autosend.days, reminderday)
                    if reminderday == today:
                        print "    That's today; send reminder now"
                        autosend.visitoccurrence.autosend(
                            EmailTemplate.NOTITY_ALL__BOOKING_REMINDER
                        )
                    else:
                        print "    That's not today. Not sending reminder"
        print "CRON job complete"


class IdleHostroleJob(CronJobBase):
    RUN_AT_TIMES = ['01:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.idlehost'

    @staticmethod
    def do():
        print "---------------------------------------------------------------"
        print "Beginning IdleHostroleJob (sends notification emails " \
              "regarding idle host roles)"

        autosends = list(VisitOccurrenceAutosend.objects.filter(
            enabled=True,
            template_key=EmailTemplate.NOTIFY_HOST__HOSTROLE_IDLE,
            days__isnull=False,
            inherit=False,
            visitoccurrence__hosts=None,
            visitoccurrence__host_status=VisitOccurrence.STATUS_NOT_ASSIGNED,
            visitoccurrence__bookings__isnull=False
        ).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitOccurrenceAutosend.objects.filter(
            inherit=True,
            template_key=EmailTemplate.NOTIFY_HOST__HOSTROLE_IDLE,
            visitoccurrence__hosts=None,
            visitoccurrence__host_status=VisitOccurrence.STATUS_NOT_ASSIGNED,
            visitoccurrence__bookings__isnull=False
        ).all())

        extra = []
        for autosend in inheriting_autosends:
            inherited = autosend.get_inherited()
            if inherited.enabled and inherited.days is not None:
                autosend.days = inherited.days
                autosend.enabled = inherited.enabled
                extra.append(autosend)
        print "Found %d enabled inheriting autosends" % len(extra)
        autosends.extend(extra)

        if len(autosends) > 0:
            today = date.today()
            print "Today is: %s" % unicode(today)

            for autosend in autosends:
                if autosend is not None:
                    print "Autosend %d for VisitOccurrence %d:" % \
                          (autosend.id, autosend.visitoccurrence.id)
                    first_booking = autosend.visitoccurrence.\
                        bookings.earliest('created_time')
                    print "    VisitOccurrence has its first booking on %s" % \
                          unicode(first_booking.created_time.date())

                    alertday = first_booking.created_time.date() + \
                        timedelta(autosend.days)
                    print "    Autosend specifies to send %d days after " \
                          "first booking, on %s" % (autosend.days, alertday)
                    if alertday == today:
                        print "    That's today; send alert now"
                        try:
                            autosend.visitoccurrence.autosend(
                                EmailTemplate.NOTIFY_HOST__HOSTROLE_IDLE
                            )
                        except Exception as e:
                            print e
                    else:
                        print "    That's not today. Not sending alert"
        print "CRON job complete"
