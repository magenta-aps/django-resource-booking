from datetime import datetime, timedelta

from django.test import TestCase
from pyquery import PyQuery
import re


from booking.models import EmailTemplateType
from booking.models import School
from booking.models import OrganizationalUnitType
from booking.models import OrganizationalUnit
from booking.models import Locality
from booking.models import RoomResponsible
from booking.models import Product
from booking.models import Subject
from booking.models import Booking
from booking.models import Visit
from booking.models import GrundskoleLevel
from booking.models import Guest
from booking.models import KUEmailMessage
from resource_booking.tests.mixins import TestMixin

from booking.models import ResourceType
from user_profile.models import UserRole

class TestBooking(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestBooking, cls).setUpClass()
        EmailTemplateType.set_defaults()
        School.create_defaults()
        GrundskoleLevel.create_defaults()
        UserRole.create_defaults()
        ResourceType.create_defaults()
        Subject.create_defaults()
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
    def test_booking_ui_sfed_timed(self):
        self._test_booking_ui(
            Product.TIME_MODE_SPECIFIC,
            Product.STUDENT_FOR_A_DAY
        )

    def test_booking_ui_sfed_suggested(self):
        self._test_booking_ui(
            Product.TIME_MODE_GUEST_SUGGESTED,
            Product.STUDENT_FOR_A_DAY
        )

    def test_booking_ui_sfed_resource(self):
        self._test_booking_ui(
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.STUDENT_FOR_A_DAY
        )





    def test_booking_ui_teacher_timed(self):
        self._test_booking_ui(
            Product.TIME_MODE_SPECIFIC,
            Product.TEACHER_EVENT,
            subjects=[s.id for s in Subject.objects.all()]
        )

    def test_booking_ui_teacher_suggested(self):
        self._test_booking_ui(
            Product.TIME_MODE_GUEST_SUGGESTED,
            Product.TEACHER_EVENT,
            desired_time='When the sun swells up',
            subjects=[s.id for s in Subject.objects.all()]
        )

    def test_booking_ui_teacher_resource(self):
        self._test_booking_ui(
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.TEACHER_EVENT,
            subjects=[s.id for s in Subject.objects.all()]
        )


    def test_booking_ui_group_timed(self):
        self._test_booking_ui(
            Product.TIME_MODE_SPECIFIC,
            Product.GROUP_VISIT
        )

    def test_booking_ui_group_suggested(self):
        self._test_booking_ui(
            Product.TIME_MODE_GUEST_SUGGESTED,
            Product.GROUP_VISIT,
            desired_datetime_date=(datetime.utcnow() + timedelta(days=12)).strftime('%d-%m-%Y')
        )

    def test_booking_ui_group_resource(self):
        self._test_booking_ui(
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.GROUP_VISIT
        )

    def test_booking_ui_project_timed(self):
        self._test_booking_ui(
            Product.TIME_MODE_SPECIFIC,
            Product.STUDY_PROJECT
        )

    def test_booking_ui_project_suggested(self):
        self._test_booking_ui(
            Product.TIME_MODE_SPECIFIC,
            Product.STUDY_PROJECT
        )
    def test_booking_ui_project_resource(self):
        self._test_booking_ui(
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.STUDY_PROJECT
        )

    def _test_booking_ui(self, time_mode, product_type, **extra_form_data):
        coordinator = self.create_default_editor(unit=self.unit)
        responsible = self.create_default_roomresponsible()
        product = self.create_product(
            self.unit,
            time_mode=time_mode,
            product_type=product_type,
            state=Product.ACTIVE
        )
        product.tilbudsansvarlig = coordinator
        product.roomresponsible.add(responsible)
        product.save()
        visit = self.create_visit(
            product,
            start=datetime.utcnow()+timedelta(days=10),
            end=datetime.utcnow()+timedelta(days=10, hours=1),
            workflow_status=Visit.WORKFLOW_STATUS_PLANNED,
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
        formdata = dict(
            **guestdata,
            **{
                'consent': 'checked',
                'repeatemail': guestdata['email'],
                'school': school.name,
                'school_type': school.type,
                'postcode': school.postcode.number,
                'city': school.postcode.city,
                'region': school.municipality.region.id,
                'notes': "some text æøå",
            },
            **extra_form_data
        )
        if product.uses_time_management:
            formdata['eventtime'] = visit.eventtime.id

        mail_types = [
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED,
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED,
            EmailTemplateType.NOTIFY_HOST__REQ_ROOM
        ]

        for t in mail_types:
            template = self.create_emailtemplate(
                key=t,
                unit=self.unit,
                subject="Booking created",
                body="Type: %d" % t
            )
            self.create_autosend(product, template.type)

        url = "/product/%d/book" % product.id

        # open booking ui, check that the form has the correct fields
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = PyQuery(response.content)
        if product_type == Product.TEACHER_EVENT:
            formdata.pop("level")

        for name in formdata.keys():
            self.assertEqual(
                1,
                len(query("input[name=%s],textarea[name=%s],select[name=%s]" % (name, name, name))),
                "%s not found" % name
            )
        count_before = KUEmailMessage.objects.count()

        # check that submission results in a new booking object
        response = self.client.post(url, formdata)
        self.assertEquals(302, response.status_code, response.content)
        self.assertEquals(
            "/product/%d/book/success?modal=0#" % product.id,
            response['Location']
        )
        booking = Booking.objects.last()
        for name in guestdata.keys():
            self.assertEquals(guestdata[name], getattr(booking.booker, name))
        if time_mode in [Product.TIME_MODE_SPECIFIC, Product.TIME_MODE_RESOURCE_CONTROLLED, Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN]:
            self.assertEquals(visit, booking.visit)
        self.assertFalse(booking.cancelled)
        self.assertIsNotNone(booking.statistics)
        self.assertEquals("some text æøå", booking.notes)

        # Check that the expected mails are sent

        message_count = KUEmailMessage.objects.count() - count_before
        # self.assertEquals(len(mail_types), KUEmailMessage.objects.count() - count_before)
        mails = {}

        for message in list(KUEmailMessage.objects.order_by('id'))[-message_count:]:
            self.assertEquals("Booking created", message.subject)
            match = re.search("Type: (\d+)", message.body)
            self.assertIsNotNone(match)
            mails[match.group(1)] = message

        self.assertEquals(3, len(mails))
        guest_key = next(
            k
            for k in [EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED, EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED]
            if str(k) in mails
        )
        self.assertEquals(
            "\"%s\" <%s>" % (coordinator.get_full_name(), coordinator.email),
            mails[str(EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED)].recipients
        )
        self.assertEquals(
            "\"%s\" <%s>" % (responsible.get_full_name(), responsible.email),
            mails[str(EmailTemplateType.NOTIFY_HOST__REQ_ROOM)].recipients
        )
        self.assertEquals(
            "\"%s %s\" <%s>" % (guestdata['firstname'], guestdata['lastname'], guestdata['email']),
            mails[str(guest_key)].recipients
        )

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
