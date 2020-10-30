from django.test import TestCase

from resource_booking.tests.mixins import TestMixin


class TestBooking(TestMixin, TestCase):

    """
    Test creation, display, editing for each type of booking
    Test workflow
    Test getters
    Test waitinglist
    Test MPVs
    """
    def test_booking_ui_timed(self):
        # create a product with visits pre-planned
        # open booking ui, check that the form has the correct fields
        # and submission results in a new booking object
        # and that the expected mails are sent
        pass

    def test_booking_ui_suggested(self):
        # create a product with bookers suggesting time
        # open booking ui, check that the form has the correct fields
        # and submission results in a new booking object
        # and that the expected mails are sent
        pass

    def test_booking_ui_resourcecontrolled(self):
        # create a resource-controlled product
        # open booking ui, check that the form has the correct fields
        # and submission results in a new booking object
        # and that the expected mails are sent
        pass

    def test_booking_display(self):
        # create product, visit, booking programmatically
        # Display booking view, check that the html is as expected, including
        # booking info
        # breadcrumb path
        # booking details
        # map url
        # send an email, check that it appears in log (mock email system)
        pass

    def test_booking_edit(self):
        # create product, visit, booking programmatically
        # Check that booking edit view displays correct data in fields
        # Post new data, checkt that booking is updated
        pass

    def test_booking_cancel(self):
        # create product, visit, booking programmatically
        # check that booking cancel ui works
        # post cancel form
        # test updated booking object
        pass
