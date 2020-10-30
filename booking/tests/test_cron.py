from django.test import TestCase


class AnonymizeEmailsJobTestCase(TestCase):
    def test_emails_before_limit_are_anonymized(self):
        pass


class AnonymizeInquirersJobTestCase(TestCase):
    def test_inquirers_before_limit_are_anonymized(self):
        pass


class AnonymizeEvaluationsJobTestCase(TestCase):
    def test_evaluations_before_limit_are_anonymized(self):
        pass


class AnonymizeGuestsJobTestCase(TestCase):
    def test_visit_guests_before_limit_are_anonymized(self):
        pass


class EvaluationReminderJobTestCase(TestCase):
    def test_evaluation_reminders_are_sent(self):
        pass


class NotifyEventTimeJobTestCase(TestCase):
    def test_event_times_are_notified(self):
        pass


class ReminderJobTestCase(TestCase):
    def test_reminder_emails_are_sent(self):
        pass


class IdleHostroleJobTestCase(TestCase):
    def idle_host_role_notifications_are_sent(self):
        pass


class RemoveOldMvpJobTestCase(TestCase):
    def old_mvp_temps_are_removed(self):
        pass
