import json
import re
from datetime import timedelta

from django.test import TestCase
from django.utils.datetime_safe import datetime
from pyquery import PyQuery as pq

from booking.models import EmailTemplate
from booking.models import EmailTemplateType
from booking.models import GrundskoleLevel
from booking.models import Guest
from booking.models import KUEmailMessage
from booking.models import OrganizationalUnit
from booking.models import OrganizationalUnitType
from booking.models import Product
from booking.models import ResourceType
from booking.models import School
from booking.models import Visit
from booking.resource_based.models import HostResource
from booking.resource_based.models import TeacherResource
from profile.models import UserRole
from resource_booking.tests.mixins import TestMixin


class TestEmail(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestEmail, cls).setUpClass()
        EmailTemplateType.set_defaults()
        UserRole.create_defaults()
        ResourceType.create_defaults()
        GrundskoleLevel.create_defaults()
        cls.unittype = OrganizationalUnitType.objects.create(name="Fakultet")
        cls.unit = OrganizationalUnit.objects.create(
            name="testunit", type=cls.unittype
        )
        cls.admin.userprofile.organizationalunit = cls.unit
        cls.admin.userprofile.save()
        """
        Test emailtemplates create, edit, preview, delete etc.
        Test autosending wrt products, visits and bookings
        """

    def test_template_list_ui(self):
        self.login("/emailtemplate", self.admin)
        self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
        )
        response = self.client.get("/emailtemplate")
        self.assertTemplateUsed(response, "email/list.html")
        query = pq(response.content)
        items = query("table tbody tr")
        found = [
            tuple([cell.text.strip() for cell in query(i).find("td")])
            for i in items
        ]
        self.assertEquals(1, len(found))
        self.assertEquals(
            EmailTemplateType.get(
                EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
            ).name,
            found[0][0]
        )
        self.assertEquals("Grundskabelon", found[0][1])

    def test_template_create_ui(self):
        self.login("/emailtemplate/create", self.admin)
        form_data = {
            'type': EmailTemplateType.get(
                EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
            ).id,
            'organizationalunit': self.unit.id,
            'subject': 'Test subject',
            'body': 'Test body'
        }
        fields = {
            'subject': None,
            'body': None
        }
        for (key, value) in fields.items():
            if type(value) != list:
                value = [value]
            for v in value:
                data = {}
                data.update(form_data)
                if v is None:
                    del data[key]
                else:
                    data[key] = v
                response = self.client.post("/emailtemplate/create", data)
                self.assertEquals(200, response.status_code)
                query = pq(response.content)
                errors = query("[name=\"%s\"]" % key) \
                    .closest("div.form-group").find("ul.errorlist li")
                self.assertEquals(1, len(errors))
        response = self.client.post("/emailtemplate/create", form_data)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/emailtemplate", response['Location'])
        for (key, value) in form_data.items():
            self.assertEquals(
                1, EmailTemplate.objects.filter(**{key: value}).count()
            )
        template = EmailTemplate.objects.get(**form_data)
        self.assertEquals(
            EmailTemplateType.get(
                EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
            ),
            template.type
        )
        self.assertEquals(self.unit, template.organizationalunit)
        self.assertEquals('Test subject', template.subject)
        self.assertEquals('Test body', template.body)

    def test_template_edit_ui(self):
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
        )
        self.login("/emailtemplate/%d/edit" % template.id, self.admin)
        form_data = {
            'type': EmailTemplateType.get(
                EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
            ).id,
            'organizationalunit': self.unit.id,
            'subject': 'Test subject',
            'body': 'Test body'
        }
        fields = {
            'subject': None,
            'body': None
        }
        for (key, value) in fields.items():
            if type(value) != list:
                value = [value]
            for v in value:
                data = {}
                data.update(form_data)
                if v is None:
                    del data[key]
                else:
                    data[key] = v
                response = self.client.post(
                    "/emailtemplate/%d/edit" % template.id, data
                )
                self.assertEquals(200, response.status_code)
                query = pq(response.content)
                errors = query("[name=\"%s\"]" % key) \
                    .closest("div.form-group").find("ul.errorlist li")
                self.assertEquals(1, len(errors))
        response = self.client.post(
            "/emailtemplate/%d/edit" % template.id, form_data
        )
        self.assertEquals(302, response.status_code)
        self.assertEquals("/emailtemplate", response['Location'])
        for (key, value) in form_data.items():
            self.assertEquals(
                1, EmailTemplate.objects.filter(**{key: value}).count()
            )
        template = EmailTemplate.objects.get(**form_data)
        self.assertEquals(EmailTemplateType.get(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED), template.type
        )
        self.assertEquals(self.unit, template.organizationalunit)
        self.assertEquals('Test subject', template.subject)
        self.assertEquals('Test body', template.body)

    def test_template_preview_ui(self):
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            subject="product.title: {{ product.title }}",
            body="product.description: {{ product.description }}"
        )
        product = self.create_product(
            unit=self.unit,
            title="Test product title",
            description="Test product description"
        )
        self.login("/emailtemplate/%d" % template.id, self.admin)
        data = {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1000,
            'form-0-type': 'Product',
            'form-0-key': 'product',
            'form-0-value': product.id
        }
        response = self.client.post(
            "/emailtemplate/%d" % template.id,
            data
        )
        response_json = json.loads(response.content)
        self.assertEquals(
            "product.title: Test product title",
            response_json['subject'].strip()
        )
        self.assertEquals(
            "product.description: Test product description",
            response_json['body'].strip()
        )

    def test_template_clone_ui(self):
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
        )
        self.login("/emailtemplate/%d/clone" % template.id, self.admin)
        form_data = {
            'type': EmailTemplateType.get(
                EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED
            ).id,
            'organizationalunit': self.unit.id,
            'subject': 'Test subject',
            'body': 'Test body'
        }
        fields = {
            'subject': None,
            'body': None
        }
        for (key, value) in fields.items():
            if type(value) != list:
                value = [value]
            for v in value:
                data = {}
                data.update(form_data)
                if v is None:
                    del data[key]
                else:
                    data[key] = v
                response = self.client.post(
                    "/emailtemplate/%d/clone" % template.id, data
                )
                self.assertEquals(200, response.status_code)
                query = pq(response.content)
                errors = query("[name=\"%s\"]" % key) \
                    .closest("div.form-group").find("ul.errorlist li")
                self.assertEquals(1, len(errors))
        response = self.client.post(
            "/emailtemplate/%d/clone" % template.id, form_data
        )
        self.assertEquals(302, response.status_code)
        self.assertEquals("/emailtemplate", response['Location'])

        template_clone = EmailTemplate.objects.get(**form_data)
        self.assertEquals(EmailTemplateType.get(
            EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED),
            template_clone.type
        )
        self.assertEquals(self.unit, template_clone.organizationalunit)
        self.assertEquals('Test subject', template_clone.subject)
        self.assertEquals('Test body', template_clone.body)
        self.assertNotEqual(template, template_clone)

    def test_template_delete_ui(self):
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            subject="Test subject",
            body="Test body"
        )
        self.login("/emailtemplate/%d/delete" % template.id, self.admin)
        response = self.client.get("/emailtemplate/%d/delete" % template.id)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        items = query("dl dt")
        data = {
            re.sub(r"[^\w ]", "", item.text.lower()): query(item).next().text()
            for item in items
        }
        self.assertDictEqual(
            {
                'type': u'Besked til g\xe6st ved tilmelding (med fast tid)',
                'enhed': 'None',
                'beskedens emne': 'Test subject',
                'beskedens tekst': 'Test body',
            },
            data
        )
        self.client.post("/emailtemplate/%d/delete" % template.id, {})
        self.assertEquals(
            0, EmailTemplate.objects.filter(id=template.id).count()
        )

    def test_autosend_visit_host_associated(self):
        from booking.booking_workflows.views import BecomeHostView
        BecomeHostView.notify_mail_template_type = \
            EmailTemplateType.notify_host__associated
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_HOST__ASSOCIATED,
            unit=self.unit,
            subject="Test association",
            body="This is a test"
        )
        host = self.create_default_host(unit=self.unit)
        HostResource.create(host, self.unit)
        product = self.create_product(
            unit=self.unit,
            potential_hosts=host
        )
        product.needed_hosts = 1
        product.save()
        self.assertListEqual([host], list(product.potential_hosts))

        visit = self.create_visit(product)
        self.create_autosend(visit, template.type)
        self.login("/visit/%d/become_host/" % visit.id, host)
        count_before = KUEmailMessage.objects.count()
        response = self.client.post(
            "/visit/%d/become_host/" % visit.id,
            {
                "confirm": "confirm"
            }
        )
        self.assertEquals(200, response.status_code)
        self.assertEquals(1, KUEmailMessage.objects.count() - count_before)
        message = KUEmailMessage.objects.last()
        self.assertEquals("Test association", message.subject.strip())
        self.assertEquals("This is a test", message.body.strip())
        self.assertEquals(
            "\"%s\" <%s>" % (host.get_full_name(), host.email),
            message.recipients
        )

    def test_autosend_visit_teacher_associated(self):
        from booking.booking_workflows.views import BecomeTeacherView
        BecomeTeacherView.notify_mail_template_type = \
            EmailTemplateType.notify_teacher__associated
        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_TEACHER__ASSOCIATED,
            unit=self.unit,
            subject="Test association",
            body="This is a test"
        )
        teacher = self.create_default_teacher(unit=self.unit)
        TeacherResource.create(teacher, self.unit)
        product = self.create_product(
            unit=self.unit,
            potential_teachers=teacher
        )
        product.needed_teachers = 1
        product.save()
        self.assertListEqual([teacher], list(product.potential_teachers))

        visit = self.create_visit(product)
        self.create_autosend(visit, template.type)
        self.login("/visit/%d/become_teacher/" % visit.id, teacher)
        count_before = KUEmailMessage.objects.count()
        response = self.client.post(
            "/visit/%d/become_teacher/" % visit.id,
            {
                "confirm": "confirm"
            }
        )
        self.assertEquals(200, response.status_code)
        self.assertEquals(1, KUEmailMessage.objects.count() - count_before)
        message = KUEmailMessage.objects.last()
        self.assertEquals("Test association", message.subject.strip())
        self.assertEquals("This is a test", message.body.strip())
        self.assertEquals(
            "\"%s\" <%s>" % (teacher.get_full_name(), teacher.email),
            message.recipients
        )

    def test_autosend_visit_booking_created(self):
        School.create_defaults()
        teacher = self.create_default_teacher(unit=self.unit)
        TeacherResource.create(teacher, self.unit)
        host = self.create_default_host(unit=self.unit)
        HostResource.create(host, self.unit)
        product = self.create_product(
            unit=self.unit,
            product_type=Product.STUDENT_FOR_A_DAY,
            state=Product.ACTIVE,
            time_mode=Product.TIME_MODE_SPECIFIC,
            potential_teachers=[teacher],
            potential_hosts=[host]
        )
        product.needed_hosts = 1
        product.needed_teachers = 1
        product.save()
        visit = self.create_visit(
            product,
            start=datetime.utcnow()+timedelta(days=10),
            end=datetime.utcnow()+timedelta(days=10, hours=1)
        )

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 1"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED_UNTIMED,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 2"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 3"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_HOST__REQ_ROOM,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 4"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 5"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 6"
        )
        self.create_autosend(visit, template.type)

        template = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE,
            unit=self.unit,
            subject="Test booking",
            body="This is a test 7"
        )
        self.create_autosend(visit, template.type)

        response = self.client.post(
            "/product/%d/book" % product.id,
            {
                'firstname': "Tester",
                'lastname': "Testersen",
                'email': "test@example.com",
                'repeatemail': "test@example.com",
                'phone': "12345678",
                'line': Guest.htx,
                'level': Guest.g3,
                'attendee_count': 10,
                'teacher_count': 1,
                'consent': True,
                'school': School.objects.first().name,
                'school_type': School.GYMNASIE,
                'eventtime': visit.eventtime.id
            }
        )
        self.assertEquals(302, response.status_code)

        emails = self.get_emails_grouped()

        guest_emails = emails[
            str(EmailTemplateType.NOTIFY_GUEST__BOOKING_CREATED)
        ]
        self.assertEquals(1, len(guest_emails))
        self.assertEquals(
            "\"Tester Testersen\" <test@example.com>",
            guest_emails[0].recipients
        )
        self.assertEquals("This is a test 1", guest_emails[0].body.strip())

        host_emails = emails[
            str(EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER)
        ]
        self.assertEquals(1, len(host_emails))
        self.assertEquals(
            "\"%s\" <%s>" % (host.get_full_name(), host.email),
            host_emails[0].recipients
        )
        self.assertEquals("This is a test 6", host_emails[0].body.strip())

        teacher_emails = emails[
            str(EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER)
        ]
        self.assertEquals(1, len(teacher_emails))
        self.assertEquals(
            "\"%s\" <%s>" % (teacher.get_full_name(), teacher.email),
            teacher_emails[0].recipients
        )
        self.assertEquals("This is a test 5", teacher_emails[0].body.strip())

        KUEmailMessage.objects.all().delete()
        visit.teachers.add(teacher)
        visit.hosts.add(host)
        visit.room_status = Visit.STATUS_NOT_NEEDED
        visit.resources_updated()

        emails = self.get_emails_grouped()
        general_emails = emails[
            str(EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE)
        ]
        self.assertEquals(3, len(general_emails))
        recipients = set([email.recipients for email in general_emails])
        self.assertSetEqual(
            set([
                u"\"%s\" <%s>" % (teacher.get_full_name(), teacher.email),
                u"\"%s\" <%s>" % (host.get_full_name(), host.email),
                u'"Tester Testersen" <test@example.com>'
            ]),
            recipients
        )
