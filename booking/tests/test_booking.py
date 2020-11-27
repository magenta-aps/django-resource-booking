from datetime import datetime, timedelta

from django.test import TestCase
from pyquery import PyQuery


from booking.models import EmailTemplateType, School, OrganizationalUnitType, \
    OrganizationalUnit, Locality, RoomResponsible, Product, Visit, \
    GrundskoleLevel, Guest
from resource_booking.tests.mixins import TestMixin


class TestBooking(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestBooking, cls).setUpClass()
        EmailTemplateType.set_defaults()
        School.create_defaults()
        GrundskoleLevel.create_defaults()
        (cls.unittype, c) = OrganizationalUnitType.objects.get_or_create(
            name="Fakultet"
        )
        (cls.unit, c) = OrganizationalUnit.objects.get_or_create(
            name="testunit", type=cls.unittype
        )
        cls.admin.userprofile.organizationalunit = cls.unit
        cls.admin.userprofile.save()
        Locality.create_defaults()
        (cls.locality, c) = Locality.objects.get_or_create(
            name='TestPlace',
            description="Place for testing",
            address_line="SomeRoad 2",
            zip_city="1234 SomeCity",
            organizationalunit=cls.unit
        )
        (cls.roomresponsible, c) = RoomResponsible.objects.get_or_create(
            name='TestResponsible',
            email='responsible@example.com',
            phone='12345678',
            organizationalunit=cls.unit
        )
    """
    Test creation, display, editing for each type of booking
    Test workflow
    Test getters
    Test waitinglist
    Test MPVs
    """
    def test_booking_ui_timed(self):

        product = self.create_product(
            self.unit,
            time_mode=Product.TIME_MODE_SPECIFIC,
            state=Product.ACTIVE
        )
        visit = self.create_visit(
            product,
            start=datetime.utcnow()+timedelta(days=10),
            end=datetime.utcnow()+timedelta(days=10, hours=1),
            workflow_status=Visit.WORKFLOW_STATUS_PLANNED
        )
        school = School.objects.first()
        guestdata = {
            'firstname': 'Tester',
            'lastname': 'Testersen',
            'email': 'guest@example.com',
            'phone': '12345678',
            'line': Guest.htx,
            'level': Guest.other,
            'attendee_count': 10,
            'school': school
        }
        school = guestdata.pop('school')
        formdata = dict(**guestdata, **{
            'consent': 'checked',
            'eventtime': visit.eventtime.id,
            'repeatemail': guestdata['email'],
            'school': school.name,
            'school_type': school.type,
            'postcode': school.postcode.number,
            'city': school.postcode.city,
            'region': school.municipality.region.id,
        })

        url = "/product/%d/book" % product.id
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = PyQuery(response.content)
        for name in formdata.keys():
            self.assertEqual(1, len(query("input[name=%s],select[name=%s]" % (name, name))))

        response = self.client.post(url, formdata)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/product/%d/book/success?modal=0#" % product.id, response['Location'])
        booking = visit.booking_list[0]
        for name in guestdata.keys():
            self.assertEquals(guestdata[name], getattr(booking.booker, name))
        # open booking ui, check that the form has the correct fields
        # and submission results in a new booking object
        # and that the expected mails are sent

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
