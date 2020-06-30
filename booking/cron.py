# coding=utf-8
from datetime import timedelta, date

from booking.models import (
    VisitAutosend,
    EmailTemplateType,
    Visit,
    Guest,
    SurveyXactEvaluation,
    KUEmailMessage,
    MultiProductVisitTemp,
    EventTime
)
import traceback

from django.db.models import Count, Q
from django.utils import timezone
from django_cron import CronJobBase, Schedule
from django_cron.models import CronJobLog

from booking.utils import surveyxact_anonymize


class KuCronJob(CronJobBase):

    description = "base KU cron job"
    code = None

    def run(self):
        pass

    def do(self):
        print "---------------------------------------------------------------"
        print "[%s] Beginning %s (%s)" % (
            unicode(timezone.now()),
            self.__class__.__name__,
            self.description
        )
        try:
            self.run()
            print "CRON job complete"
        except:
            print traceback.format_exc()
            print "CRON job failed"
            raise

    def get_last_run(self):
        try:
            return CronJobLog.objects.filter(
                code=self.code,
                is_success=True,
                ran_at_time__isnull=True
            ).latest('start_time')
        except CronJobLog.DoesNotExist:
            pass


class ReminderJob(KuCronJob):
    RUN_AT_TIMES = ['01:00']

    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.reminders'
    description = "sends reminder emails"

    def run(self):
        emailtemplatetypes = [
            EmailTemplateType.notity_all__booking_reminder,
            EmailTemplateType.notify_guest_reminder
        ]
        autosends = list(VisitAutosend.objects.filter(
            enabled=True,
            template_type__in=emailtemplatetypes,
            days__isnull=False,
            inherit=False,
            visit__eventtime__start__isnull=False,
            visit__eventtime__start__gte=timezone.now()
        ))
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitAutosend.objects.filter(
            inherit=True,
            template_type__in=emailtemplatetypes,
            visit__eventtime__start__isnull=False,
            visit__eventtime__start__gte=timezone.now()
        ).all())

        extra = []
        for autosend in inheriting_autosends:
            inherited = autosend.get_inherited()
            if inherited is not None and \
                    inherited.enabled and \
                    inherited.days is not None:
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
                    start = autosend.visit.eventtime.start
                    if start is not None:
                        print "    Visit starts on %s" % unicode(start)
                        reminderday = start.date() - timedelta(autosend.days)
                        print "    Autosend specifies to send %d days prior," \
                              " on %s" % (autosend.days, reminderday)
                        if reminderday == today:
                            print "    That's today; send reminder now"
                            autosend.visit.autosend(
                                autosend.template_type
                            )
                        else:
                            print "    That's not today. Not sending reminder"
                    else:
                        print "    Visit has no start date"


class IdleHostroleJob(KuCronJob):
    RUN_AT_TIMES = ['01:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.idlehost'
    description = "sends notification emails regarding idle host roles"

    def run(self):

        visit_qs = Visit.objects.annotate(
            num_bookings=Count('bookings'),
        ).filter(
            num_bookings__gt=0,
            workflow_status__in=[
                Visit.WORKFLOW_STATUS_BEING_PLANNED,
                Visit.WORKFLOW_STATUS_REJECTED,
                Visit.WORKFLOW_STATUS_AUTOASSIGN_FAILED
            ]
        )
        visits_needing_hosts = [
            visit for visit in visit_qs if visit.needs_hosts
        ]

        autosends = list(VisitAutosend.objects.filter(
            enabled=True,
            template_type=EmailTemplateType.notify_host__hostrole_idle,
            days__isnull=False,
            inherit=False,
            visit__in=visits_needing_hosts
        ).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitAutosend.objects.filter(
            inherit=True,
            template_type=EmailTemplateType.notify_host__hostrole_idle,
            visit__in=visits_needing_hosts
        ).all())

        extra = []
        for autosend in inheriting_autosends:
            inherited = autosend.get_inherited()
            if inherited is not None and \
                    inherited.enabled and \
                    inherited.days is not None:
                autosend.days = inherited.days
                autosend.enabled = inherited.enabled
                extra.append(autosend)
        print "Found %d enabled inheriting autosends" % len(extra)
        autosends.extend(extra)

        try:
            if len(autosends) > 0:
                today = date.today()
                print "Today is: %s" % unicode(today)

                for autosend in autosends:
                    if autosend is None:
                        continue
                    print "Autosend %d for Visit %d:" % \
                          (autosend.id, autosend.visit.id)
                    first_booking = autosend.visit.\
                        bookings.earliest('statistics__created_time')
                    print "    Visit has its first booking on %s" % \
                          unicode(
                              first_booking.statistics.created_time.date()
                          )

                    alertday = first_booking.statistics.created_time.\
                        date() + timedelta(autosend.days)
                    print "    Autosend specifies to send %d days after " \
                          "first booking, on %s" % (autosend.days, alertday)
                    if alertday == today:
                        print "    That's today; send alert now"
                        try:
                            autosend.visit.autosend(
                                EmailTemplateType.notify_host__hostrole_idle
                            )
                        except Exception as e:
                            print e
                    else:
                        print "    That's not today. Not sending alert"
        finally:
            for autosend in autosends:
                autosend.refresh_from_db()


class RemoveOldMvpJob(KuCronJob):
    RUN_AT_TIMES = ['01:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.removempv'
    description = "deletes obsolete mvp temps"

    def run(self):
        MultiProductVisitTemp.objects.filter(
            updated__lt=timezone.now()-timedelta(days=1)
        ).delete()


class NotifyEventTimeJob(KuCronJob):
    schedule = Schedule(run_every_mins=0)
    code = 'kubooking.notifyeventtime'
    description = "notifies EventTimes that they're starting/ending"

    def run(self):
        prev = self.get_last_run()
        if prev:
            end = timezone.now()
            print "Notifying eventtimes before %s" % (unicode(end))

            for eventtime in EventTime.objects.filter(
                    has_notified_start=False,
                    start__lt=end
            ):
                print "Notifying EventTime %d (starting)" % eventtime.id
                eventtime.on_start()

            for eventtime in EventTime.objects.filter(
                    has_notified_end=False,
                    end__lt=end
            ):
                print "Notifying EventTime %d (ending)" % eventtime.id
                eventtime.on_end()


class EvaluationReminderJob(KuCronJob):
    RUN_AT_TIMES = ['02:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.evaluationreminder'
    description = "sends evaluation reminder emails"
    days = 5

    def run(self):
        emailtemplate = [
            EmailTemplateType.notify_guest__evaluation_second,
            EmailTemplateType.notify_guest__evaluation_second_students
        ]
        filter = {
            'template_type__in': emailtemplate,
        }

        autosends = list(VisitAutosend.objects.filter(
            inherit=False,
            enabled=True,
            days__isnull=False,
        ).filter(**filter).all())
        print "Found %d enabled autosends" % len(autosends)

        inheriting_autosends = list(VisitAutosend.objects.filter(
            inherit=True,
        ).filter(**filter).all())

        extra = []
        for autosend in inheriting_autosends:
            inherited = autosend.get_inherited()
            if inherited is not None and inherited.enabled:
                autosend.enabled = inherited.enabled
                extra.append(autosend)
        print "Found %d enabled inheriting autosends" % len(extra)
        autosends.extend(extra)

        try:
            if len(autosends):
                today = date.today()
                print "Today is: %s" % unicode(today)
                for autosend in autosends:
                    visit = autosend.visit
                    print "Autosend %d for Visit %d:" % \
                          (autosend.id, visit.id)
                    if visit.end_datetime is None:
                        print "Visit %d has no apparent end_datetime" %\
                              visit.id
                    else:
                        print "    Visit ends on %s" % \
                              unicode(visit.end_datetime.date())
                        alertday = visit.end_datetime.date() + \
                            timedelta(self.days)
                        print "    Hardcoded to send %d days after " \
                              "completion, on %s" % (self.days, alertday)
                        if alertday == today:
                            print "    That's today; sending messages now"
                            product = visit.product
                            if product is not None:
                                evals = product.surveyxactevaluation_set.all()
                                for evaluation in evals:
                                    evaluation.send_second_notification(visit)

                        else:
                            print "    That's not today. Not sending messages"
        finally:
            for autosend in autosends:
                autosend.refresh_from_db()


class AnonymizeGuestsJob(KuCronJob):
    RUN_AT_TIMES = ['00:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.anonymize.guests'
    description = "Anonymizes guests for visits that were held in the past"

    def run(self):
        limit = timezone.now() - timedelta(days=365*2)
        guests = Guest.objects.filter(
            Q(booking__visit__eventtime__start__lt=limit) |
            Q(booking__visit__cancelled_eventtime__start__lt=limit)
        ).exclude(
            Guest.filter_anonymized()
        )
        for guest in guests:
            visit = guest.booking.visit
            if hasattr(visit, 'eventtime'):
                time = visit.eventtime.start
            elif visit.cancelled_eventtime is not None:
                time = visit.cancelled_eventtime.start
            print "Anonymizing guest #%d on visit %d (starttime %s)" % \
                  (guest.id, visit.id, time)
            guest.anonymize()


class AnonymizeEvaluationsJob(KuCronJob):
    RUN_AT_TIMES = ['00:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.anonymize.evaluations'
    description = "Anonymizes evaluations that were filled out in the past"

    def run(self):
        survey_ids = set([
            evaluation.surveyId
            for evaluation in SurveyXactEvaluation.objects.distinct('surveyId')
        ])
        limit = timezone.now() - timedelta(days=365*2)
        for survey_id in survey_ids:
            print "Anonymizing survey %d" % survey_id
            success = surveyxact_anonymize(survey_id, limit)
            if not success:
                print "Failed anonymizing survey %d" % survey_id


class AnonymizeInquirersJob(KuCronJob):
    RUN_AT_TIMES = ['00:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.anonymize.inquirers'
    description = "Anonymizes inquirers that asked about products"

    def run(self):
        limit = timezone.now() - timedelta(days=365*2)
        messages = KUEmailMessage.objects.filter(
            template_type__key=EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE,
            created__lt=limit
        )
        messages.delete()


class AnonymizeEmailsJob(KuCronJob):
    RUN_AT_TIMES = ['00:00']
    schedule = Schedule(run_at_times=RUN_AT_TIMES)
    code = 'kubooking.anonymize.emails'
    description = "Anonymizes emails"

    def run(self):
        limit = timezone.now() - timedelta(days=365*2)
        messages = KUEmailMessage.objects.filter(
            created__lt=limit,
        ).exclude(
            **KUEmailMessage.anonymized_filter
        )
        for message in messages:
            message.anonymize()
