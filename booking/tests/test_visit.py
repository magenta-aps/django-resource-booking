# encoding: utf-8

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils.datetime_safe import datetime
from pyquery import PyQuery

from booking.models import Product, KUEmailRecipient, EmailTemplateType, \
    RoomResponsible, ResourceType, OrganizationalUnitType, School, \
    OrganizationalUnit, Locality
from user_profile.models import UserRole
from resource_booking.tests.mixins import TestMixin, ParsedNode
from django.test import TestCase


class TestVisit(TestMixin, TestCase):

    """
    Test creation, display, editing for each type of visit
    Test workflow
    Test getters
    Test waitinglist
    Test MPVs
    """
    @classmethod
    def setUpClass(cls):
        super(TestVisit, cls).setUpClass()
        EmailTemplateType.set_defaults()
        School.create_defaults()
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

    def test_email_recipients(self):
        # setup visits with users in different roles
        # test that get_recipients returns the correct users
        EmailTemplateType.set_defaults()
        ResourceType.create_defaults()
        UserRole.create_defaults()
        teacher = self.create_default_teacher(unit=self.unit)
        host = self.create_default_host(unit=self.unit)
        coordinator = self.create_default_coordinator(unit=self.unit)
        roomguy = self.create_default_roomresponsible(unit=self.unit)
        teacher_pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_TEACHER,
            self.unit,
            'test_teacher_pool',
            teacher.userprofile.get_resource()
        )
        host_pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_HOST,
            self.unit,
            'test_host_pool',
            teacher.userprofile.get_resource()
        )

        visits = []

        for product_type, label in Product.resource_type_choices:
            for time_mode in [
                Product.TIME_MODE_SPECIFIC,
                Product.TIME_MODE_GUEST_SUGGESTED, Product.TIME_MODE_NO_BOOKING
            ]:
                product = self.create_product(
                    self.unit,
                    time_mode=time_mode,
                    potential_teachers=[teacher],
                    potential_hosts=[host],
                    state=Product.CREATED,
                    product_type=product_type
                )
                product.tilbudsansvarlig = coordinator
                product.roomresponsible.add(roomguy)
                product.save()

                start = datetime.utcnow() + timedelta(days=10)
                visit = self.create_visit(
                    product,
                    start,
                    start + timedelta(hours=1)
                )
                visit.teachers.add(teacher)
                # not adding host - hosts behave the same as teachers,
                # and we want to check the case where no host is assigned
                # (potential hosts will get mail, assigned hosts will not)
                visit.save()
                visits.append(visit)

        for time_mode in [
            Product.TIME_MODE_RESOURCE_CONTROLLED,
            Product.TIME_MODE_RESOURCE_CONTROLLED_AUTOASSIGN
        ]:
            product = self.create_product(
                self.unit,
                time_mode=time_mode,
                state=Product.CREATED,
                product_type=product_type
            )
            product.tilbudsansvarlig = coordinator
            product.roomresponsible.add(roomguy)
            self.create_resourcerequirement(product, teacher_pool, 1)
            self.create_resourcerequirement(product, host_pool, 1)
            product.save()
            start = datetime.utcnow() + timedelta(days=10)
            visit = self.create_visit(
                product,
                start,
                start + timedelta(hours=1)
            )
            visit.teachers.add(teacher)
            # not adding host - hosts behave the same as teachers,
            # and we want to check the case where no host is assigned
            # (potential hosts will get mail, assigned hosts will not)
            visit.save()
            # visits.append(visit)

        expected = {
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator)
            ],
            EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER: [
                (KUEmailRecipient.TYPE_HOST, host)
            ],
            EmailTemplateType.NOTIFY_HOST__REQ_ROOM: [
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy)
            ],
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy),
                (KUEmailRecipient.TYPE_TEACHER, teacher)
            ],
            EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy),
                (KUEmailRecipient.TYPE_TEACHER, teacher)
            ],
            EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy),
                (KUEmailRecipient.TYPE_TEACHER, teacher)
            ],
            EmailTemplateType.NOTIFY_HOST__HOSTROLE_IDLE: [
                (KUEmailRecipient.TYPE_EDITOR, coordinator)
            ],
            EmailTemplateType.NOTIFY_EDITORS__SPOT_REJECTED: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
            ],
        }

        expected.update({
            template_type.key: []
            for template_type in EmailTemplateType.objects.all()
            if template_type.key not in expected.keys()
        })

        def unpack(item):
            if isinstance(item, User):
                return (item.get_full_name(), item.email)
            if isinstance(item, RoomResponsible):
                return (item.name, item.email)

        for visit in visits:
            for template_type_key, expected_recipients in expected.items():
                actual_recipients = visit.get_recipients(
                    EmailTemplateType.get(template_type_key)
                )
                self.assertEquals(
                    len(expected_recipients), len(actual_recipients),
                    "Expected number of recipients not "
                    "matching for template type %d (%d vs %d)" % (
                        template_type_key,
                        len(expected_recipients),
                        len(actual_recipients)
                    )
                )
                expected_recipients = [
                    (t, unpack(r))
                    for (t, r) in expected_recipients
                ]
                for r in actual_recipients:
                    self.assertTrue(
                        (r.type, (r.name, r.email)) in expected_recipients,
                        "did not expect (%d, (%s, %s)) "
                        "for template type %d, expected %s" %
                        (
                            r.type, r.name, r.email,
                            template_type_key, str(expected_recipients)
                        )
                    )

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

        ResourceType.create_defaults()
        UserRole.create_defaults()
        School.create_defaults()
        teacher = self.create_default_teacher(unit=self.unit)
        host = self.create_default_host(unit=self.unit)
        coordinator = self.create_default_coordinator(unit=self.unit)
        roomguy = self.create_default_roomresponsible(unit=self.unit)
        self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_TEACHER,
            self.unit,
            'test_teacher_pool',
            teacher.userprofile.get_resource()
        )
        self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_HOST,
            self.unit,
            'test_host_pool',
            teacher.userprofile.get_resource()
        )

        product = self.create_product(
            self.unit,
            time_mode=Product.TIME_MODE_SPECIFIC
        )
        product.roomresponsible.add(roomguy)
        product.tilbudsansvarlig = coordinator
        product.do_create_waiting_list = True
        product.waiting_list_length = 10
        product.maximum_number_of_visitors = 10
        product.save()
        start = datetime.utcnow() + timedelta(days=10)
        visit = self.create_visit(product, start, start + timedelta(hours=1))
        visit.teachers.add(teacher)
        visit.hosts.add(host)
        visit.save()

        guest1 = self.create_guest("Tester1")
        guest1.attendee_count = 10
        guest1.school = School.objects.get(id=1)
        guest1.save()
        self.create_booking(visit, guest1)
        guest2 = self.create_guest("Tester2")
        guest2.attendee_count = 10
        guest2.school = School.objects.get(id=2)
        guest2.save()
        booking2 = self.create_booking(visit, guest2)
        booking2.waitinglist_spot = 1
        booking2.save()

        url = "/visit/%d/" % visit.id
        self.login(url, self.admin)
        response = self.client.get(url)
        query = PyQuery(response.content)
        self.assertEquals(
            "10 har tilmeldt sig testproduct",
            query("#attendees").text()
        )

        overview = ParsedNode(query("#status-overview"))
        data = {}
        for row in overview.find("div.row"):
            key = None
            values = []
            for c in row.children:
                if c.tag == 'strong':
                    key = unicode(c.text)
                elif c.tag == 'div':
                    values.append(unicode(c.text))
            data[key] = values
        self.assertDictEqual(
            {
                u'Enhed': [u'testunit'],
                u'Tidspunkt': [
                    product.eventtime_set.first().interval_display, u'Redigér'
                ],
                u'Undervisere': [u'1/0 undervisere fundet', u'Redigér'],
                u'Værter': [u'1/0 værter fundet', u'Redigér'],
                u'Lokaler': [u'Afventer tildeling/bekræftelse', u'Redigér'],
                u'Automatisk e-mail': [u'', u'Redigér'],
                u'Status': [u'Under planlægning', u'Skift status'],
                u'Antal på venteliste': [u'10', u'Se liste'],
                u'Vigtig bemærkning': [u'', u'Redigér']
            },
            data
        )

        attendees_overview = ParsedNode(query(".attendees"))
        self.assertEquals(
            "Tilmeldte\n(10/10)",
            self.strip_inner(attendees_overview.find("h2")[0].text)
        )
        attendees_list = attendees_overview.find(".list-group-item")
        for attendee in attendees_list:
            data = {}
            for d in [x.extract_dl() for x in attendee.find("dl")]:
                data.update(d)
            self.assertDictEqual(
                {
                    u'koordinator:': [{'text': coordinator.get_full_name()}],
                    u'studieretning:': [{'text': None}],
                    u'fag:': [],
                    u'underviser:': [{'text': teacher.get_full_name()}],
                    u'antal:': [{'text': '10'}],
                    u'email:': [{'text': guest1.email}],
                    u'vært:': [{'text': host.get_full_name()}],
                    u'niveau:': [{'text': 'Afsluttet gymnasieuddannelse'}],
                    u'navn:': [{'text': guest1.get_full_name()}],
                    u'skole:': [
                        {
                            'text': 'Aabenraa Statsskole, 6200 Aabenraa',
                            'children': [
                                {'text': 'Aabenraa Statsskole, 6200 Aabenraa'}
                            ]
                        }
                    ]
                },
                data
            )

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

    def test_profile_page(self):
        # create several products with visits, assigned to different users
        # test that the visits show up on the profile page
        # for the relevant users
        # test the product type filtering
        pass
