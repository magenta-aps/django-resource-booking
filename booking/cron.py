from datetime import timedelta, date

from booking.models import VisitAutosend, EmailTemplateType, Visit
from booking.models import MultiProductVisitTemp
from django_cron import CronJobBase, Schedule


class ReminderJob(CronJobBase):
    RUN_AT_TIMES = ['01:00']

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.reminders'

    def do(self):
        print "---------------------------------------------------------------"
        print "Beginning ReminderJob (sends reminder emails)"
        autosends = list(VisitAutosend.objects.filter(
            enabled=True,
            template_key=EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER,
            days__isnull=False,
            inherit=False
        ).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitAutosend.objects.filter(
            inherit=True,
            template_key=EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER,
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
                    print "Autosend %d for Visit %d:" % \
                        (autosend.id, autosend.visit.id)
                    print "    Visit starts on %s" % \
                        unicode(autosend.visit.start_datetime.date())
                    reminderday = autosend.visit.\
                        start_datetime.date() - \
                        timedelta(autosend.days)
                    print "    Autosend specifies to send %d " \
                          "days prior, on %s" % (autosend.days, reminderday)
                    if reminderday == today:
                        print "    That's today; send reminder now"
                        autosend.visit.autosend(
                            EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER
                        )
                    else:
                        print "    That's not today. Not sending reminder"
        print "CRON job complete"


class IdleHostroleJob(CronJobBase):
    RUN_AT_TIMES = ['01:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.idlehost'

    def do(self):
        print "---------------------------------------------------------------"
        print "Beginning IdleHostroleJob (sends notification emails " \
              "regarding idle host roles)"

        autosends = list(VisitAutosend.objects.filter(
            enabled=True,
            template_key=EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE,
            days__isnull=False,
            inherit=False,
            visit__hosts=None,
            visit__host_status=Visit.STATUS_NOT_ASSIGNED,
            visit__bookings__isnull=False
        ).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitAutosend.objects.filter(
            inherit=True,
            template_key=EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE,
            visit__hosts=None,
            visit__host_status=Visit.STATUS_NOT_ASSIGNED,
            visit__bookings__isnull=False
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
                    print "Autosend %d for Visit %d:" % \
                          (autosend.id, autosend.visit.id)
                    first_booking = autosend.visit.\
                        bookings.earliest('statistics__created_time')
                    print "    Visit has its first booking on %s" % \
                          unicode(first_booking.statistics.created_time.date())

                    alertday = first_booking.statistics.created_time.date() + \
                        timedelta(autosend.days)
                    print "    Autosend specifies to send %d days after " \
                          "first booking, on %s" % (autosend.days, alertday)
                    if alertday == today:
                        print "    That's today; send alert now"
                        try:
                            autosend.visit.autosend(
                                EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE
                            )
                        except Exception as e:
                            print e
                    else:
                        print "    That's not today. Not sending alert"
        print "CRON job complete"


class RemoveOldMvpJob(CronJobBase):
    RUN_AT_TIMES = ['01:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.removempv'

    def do(self):
        print "---------------------------------------------------------------"
        print "Beginning RemoveOldMvpJob (deletes obsolete mvp temps)"
        MultiProductVisitTemp.objects.filter(
            updated__lt=timezone.now()-timedelta(days=1)
        ).delete()
        print "CRON job complete"
