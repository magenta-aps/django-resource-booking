from resource_booking.tests.mixins import TestMixin
from django.test import TestCase


class TestVisit(TestMixin, TestCase):

    """
    Test creation, display, editing for each type of visit
    Test workflow
    Test getters
    Test waitinglist
    Test MPVs
    """

    def test_email_recipients(self):
        # setup visits with users in different roles
        # test that get_recipients returns the correct users
        pass

    def test_visit_ui(self):
        # create product, visit and bookings
        # test that visit view html looks ok, including
        # number of attendees
        # time
        # status data
        # booker list
        # waiting list
        # activity log
        # emails
        # Post log form, check that new log entry is created
        # Post comment form, check that new log entry is created
        # test that bookings can be moved to/from waiting list
        # test that bookings can be deleted
        pass

    def test_visit_edit(self):
        # test editing of visit components
        # time
        # teachers
        # hosts
        # rooms
        # autosends
        # workflow status
        # comments
        pass
