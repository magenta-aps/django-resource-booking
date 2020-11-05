from datetime import timedelta, datetime

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from freezegun import freeze_time

from django_cron.models import CronJobLog

from resource_booking.tests.mixins import TestMixin

from booking.models import (
    MultiProductVisitTemp,
    Visit,
    Guest,
    KUEmailMessage,
    EmailTemplateType,
    SurveyXactEvaluationGuest,
    OrganizationalUnit,
    OrganizationalUnitType,
)
from booking.cron import (
    RemoveOldMvpJob,
    NotifyEventTimeJob,
    AnonymizeGuestsJob,
    EvaluationReminderJob,
    AnonymizeEvaluationsJob,
    AnonymizeEmailsJob,
    AnonymizeInquirersJob,
)
import unittest.mock


class AnonymizeEmailsJobTestCase(TestCase):
    def test_emails_before_limit_are_anonymized(self):
        less_than_two_years_ago = timezone.now() - timedelta(days=(365 * 2) + 1)
        with freeze_time(less_than_two_years_ago):
            email = KUEmailMessage.objects.create()

        job = AnonymizeEmailsJob()
        job.run()

        email.refresh_from_db()
        self.assertEqual(email.recipients, KUEmailMessage.anonymized)
        self.assertEqual(email.body, KUEmailMessage.anonymized)
        self.assertEqual(email.htmlbody, KUEmailMessage.anonymized)


class AnonymizeInquirersJobTestCase(TestCase, TestMixin):
    def test_inquirers_before_limit_are_anonymized(self):
        less_than_two_years_ago = timezone.now() - timedelta(days=(365 * 2) + 1)

        template_type = EmailTemplateType.objects.create(
            key=EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE
        )

        with freeze_time(less_than_two_years_ago):
            email = KUEmailMessage.objects.create(
                template_type=template_type,
                template_key=EmailTemplateType.SYSTEM__BASICMAIL_ENVELOPE,
            )

        job = AnonymizeInquirersJob()
        job.run()

        with self.assertRaises(ObjectDoesNotExist):
            email.refresh_from_db()


class AnonymizeEvaluationsJobTestCase(TestCase, TestMixin):
    @unittest.mock.patch("booking.cron.surveyxact_anonymize")
    def test_evaluations_before_limit_are_anonymized(self, anonymize_mock):
        now = timezone.now()
        two_years_ago = now - timedelta(days=365 * 2)
        # Create an evaluation before limit.
        with freeze_time(two_years_ago):
            product = self.create_product()
            evaluation = self.create_evaluation(product)
        # Run Anonymization job.
        with freeze_time(now):
            job = AnonymizeEvaluationsJob()
            job.run()
        # Assert anonymization function is called.
        anonymize_mock.assert_called_with(evaluation.surveyId, two_years_ago)


class AnonymizeGuestsJobTestCase(TestCase, TestMixin):
    def test_visit_guests_before_limit_are_anonymized(self):
        # Set up a guest with an old booking
        guest = self.create_guest()
        product = self.create_product()
        visit = self.create_visit(
            product,
            start=datetime.now() - timedelta(days=(365 * 2) + 1),
            end=datetime.now() - timedelta(days=365 * 2),
        )
        self.create_booking(visit, guest)

        job = AnonymizeGuestsJob()
        job.run()

        self.assertIn(guest, Guest.objects.filter(Guest.filter_anonymized()))


class EvaluationReminderJobTestCase(TestCase, TestMixin):
    def test_evaluation_reminders_are_sent(self):
        guest = self.create_guest()
        unit = self.create_organizational_unit()
        product = self.create_product(unit=unit)
        evaluation = self.create_evaluation(
            product
        )
        evaluation_guest = SurveyXactEvaluationGuest.objects.create(
            status=SurveyXactEvaluationGuest.STATUS_FIRST_SENT,
            evaluation=evaluation,
            guest=guest
        )
        visit = self.create_visit(
            product,
            start=datetime.now() - timedelta(days=10),
            end=datetime.now() - timedelta(days=5),
        )
        booking = self.create_booking(visit, guest)
        template_type = EmailTemplateType.objects.create(
            key=EmailTemplateType.NOTIFY_GUEST__EVALUATION_SECOND,
            name_da="gæst evaluering anden",
        )
        email_template = self.create_emailtemplate(
            type=template_type
        )

        autosend = self.create_autosend(visit, template_type, enabled=True, days=5)
        job = EvaluationReminderJob()
        job.run()

        evaluation_guest.refresh_from_db()
        self.assertEqual(evaluation_guest.status, SurveyXactEvaluationGuest.STATUS_SECOND_SENT)


class NotifyEventTimeJobTestCase(TestCase, TestMixin):
    def test_event_times_are_notified_start(self):
        product = self.create_product()

        visit = self.create_visit(
            product,
            start=datetime.now() - timedelta(days=1),
            end=datetime.now() + timedelta(days=1),
            workflow_status=Visit.WORKFLOW_STATUS_PLANNED,
        )

        job = NotifyEventTimeJob()
        CronJobLog.objects.create(
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() - timedelta(days=1),
            code=job.code,
            is_success=True,
        )
        job.run()

        visit.refresh_from_db()
        visit.eventtime.refresh_from_db()
        self.assertTrue(visit.eventtime.has_notified_start)

    def test_event_times_are_notified_end(self):
        product = self.create_product()

        visit = self.create_visit(
            product,
            start=datetime.now() - timedelta(days=2),
            end=datetime.now() - timedelta(days=1),
            workflow_status=Visit.WORKFLOW_STATUS_PLANNED,
        )

        job = NotifyEventTimeJob()
        CronJobLog.objects.create(
            start_time=timezone.now() - timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1),
            code=job.code,
            is_success=True,
        )
        job.run()

        visit.refresh_from_db()
        visit.eventtime.refresh_from_db()
        self.assertTrue(visit.eventtime.has_notified_end)
        self.assertEqual(visit.workflow_status, Visit.WORKFLOW_STATUS_EXECUTED)


class ReminderJobTestCase(TestCase):
    def test_reminder_emails_are_sent(self):
        pass


class IdleHostroleJobTestCase(TestCase):
    def test_idle_host_role_notifications_are_sent(self):
        pass


class RemoveOldMvpJobTestCase(TestCase):
    def test_old_mvp_temps_are_removed(self):
        # Create an old MultiProductVisitTemp to be deleted.
        with freeze_time(timezone.now() - timedelta(days=1)):
            to_be_deleted = MultiProductVisitTemp.objects.create(
                date=timezone.now() - timedelta(days=1)
            )

        # Create a new MultiProductVisitTemp today.
        MultiProductVisitTemp.objects.create(date=timezone.now())

        job = RemoveOldMvpJob()
        job.run()

        self.assertEqual(MultiProductVisitTemp.objects.count(), 1)
        with self.assertRaises(ObjectDoesNotExist):
            to_be_deleted.refresh_from_db()
