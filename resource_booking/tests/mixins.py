from datetime import timedelta

import backports.unittest_mock
import pytz
from django.contrib.auth.models import User
from django.test.client import Client
from django.utils.datetime_safe import datetime

from booking.models import EmailTemplate
from booking.models import EmailTemplateType
from booking.models import EventTime
from booking.models import KUEmailMessage
from booking.models import Product
from booking.models import ProductAutosend
from booking.models import Visit
from booking.models import VisitAutosend
from booking.resource_based.models import ResourcePool, ResourceRequirement
from profile.constants import ADMINISTRATOR
from profile.constants import COORDINATOR
from profile.constants import FACULTY_EDITOR
from profile.constants import HOST
from profile.constants import TEACHER
from profile.models import UserRole, UserProfile

backports.unittest_mock.install()  # noqa
from unittest.mock import patch


class TestMixin(object):

    admin = None

    def __init__(self, *args, **kwargs):
        super(TestMixin, self).__init__(*args, **kwargs)
        self.client = None

    @classmethod
    def setUpClass(cls):
        super(TestMixin, cls).setUpClass()
        (cls.admin, c) = User.objects.get_or_create(
            {'is_superuser': True},
            username="admin"
        )
        cls.admin.set_password('admin')
        cls.admin.save()
        (role, created) = UserRole.objects.get_or_create(
            {'name': u"Administrator"},
            role=ADMINISTRATOR
        )
        (adminprofile, c) = UserProfile.objects.get_or_create(
            {'user_role': role},
            user=cls.admin,
        )
        adminprofile.save()

    def setUp(self):
        super(TestMixin, self).setUp()
        self.client = Client()

    def login(self, url, user):
        response = self.client.get(url)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/profile/login?next=%s" % url, response['Location'])
        # self.client.login(username="admin", password="admin")
        self.client.force_login(user)

    def mock(self, method):
        patch_object = patch(method)
        mock_object = patch_object.start()
        self.addCleanup(patch_object.stop)
        return mock_object

    @staticmethod
    def get_file_contents(filename):
        with open(filename, "r") as f:
            return f.read()

    def compare(self, a, b, path):
        self.assertEqual(
            type(a), type(b),
            "mismatch on %s, different type %s != %s"
            % (path, type(a), type(b))
        )
        if isinstance(a, list):
            self.assertEqual(
                len(a), len(b),
                "mismatch on %s, different length %d != %d"
                % (path, len(a), len(b))
            )
            for index, item in enumerate(a):
                self.compare(item, b[index], "%s[%d]" % (path, index))
        elif isinstance(a, dict):
            self.compare(a.keys(), b.keys(), "%s.keys()" % path)
            for key in a:
                self.compare(a[key], b[key], "%s[%s]" % (path, key))
        else:
            self.assertEqual(
                a, b,
                "mismatch on %s, different value %s != %s" % (path, a, b)
            )

    def create_user(
            self, username, email, role,
            first_name=None, last_name=None, unit=None
    ):
        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email
        )
        user.save()
        profile = UserProfile(
            user=user,
            user_role=UserRole.objects.filter(role=role).first(),
            organizationalunit=unit
        )
        profile.save()
        return user

    def create_default_teacher(
            self, username="test_teacher", email="test_teacher@example.com",
            first_name="test", last_name="teacher", unit=None
    ):
        return self.create_user(
            username,
            email,
            TEACHER,
            first_name,
            last_name,
            unit
        )

    def create_default_host(
            self, username="test_host", email="test_host@example.com",
            first_name="test", last_name="host", unit=None
    ):
        return self.create_user(
            username,
            email,
            HOST,
            first_name,
            last_name,
            unit
        )

    def create_default_coordinator(
            self, username="test_coordinator",
            email="test_coordinator@example.com", first_name="test",
            last_name="coordinator", unit=None
    ):
        return self.create_user(
            username,
            email,
            COORDINATOR,
            first_name,
            last_name,
            unit
        )

    def create_default_editor(
            self, username="test_editor", email="test_editor@example.com",
            first_name="test", last_name="editor", unit=None
    ):
        return self.create_user(
            username,
            email,
            FACULTY_EDITOR,
            first_name,
            last_name,
            unit
        )

    def create_product(
            self, unit=None, title="testproduct", teaser="for testing",
            description="this is a test product",
            time_mode=Product.TIME_MODE_NONE,
            potential_teachers=None, potential_hosts=None,
            state=Product.CREATED,
            product_type=Product.STUDENT_FOR_A_DAY,
    ):
        product = Product(
            title=title,
            teaser=teaser,
            description=description,
            organizationalunit=unit,
            time_mode=time_mode,
            state=state,
            type=product_type,
        )
        product.save()
        if potential_teachers is not None:
            if type(potential_teachers) != list:
                potential_teachers = [potential_teachers]
            for teacher in potential_teachers:
                product.potentielle_undervisere.add(teacher)
        if potential_hosts is not None:
            if type(potential_hosts) != list:
                potential_hosts = [potential_hosts]
            for host in potential_hosts:
                product.potentielle_vaerter.add(host)
        return product

    def create_visit(
            self,
            product,
            start=datetime.utcnow(),
            end=datetime.utcnow() + timedelta(hours=1),
            workflow_status=Visit.WORKFLOW_STATUS_BEING_PLANNED
    ):
        visit = Visit(
            workflow_status=workflow_status
        )
        visit.save()
        eventtime = EventTime(
            product=product,
            visit=visit,
            start=pytz.utc.localize(start),
            end=pytz.utc.localize(end)
        )
        eventtime.save()
        return visit

    def create_emailtemplate(
            self,
            key=1,
            type=None,
            subject="",
            body="",
            unit=None
    ):
        if key is not None and type is None:
            type = EmailTemplateType.get(key)
        template = EmailTemplate(
            key=key,
            type=type,
            subject=subject,
            body=body,
            organizationalunit=unit
        )
        template.save()
        return template

    def create_resourcepool(self, name, type, unit, *resources):
        resourcepool = ResourcePool(
            name=name,
            resource_type=type,
            organizationalunit=unit
        )
        resourcepool.save()
        for resource in resources:
            resourcepool.resources.add(resource)
        return resourcepool

    def create_resourcerequirement(self, product, pool, amount):
        requirement = ResourceRequirement(
            product=product,
            resource_pool=pool,
            required_amount=amount
        )
        requirement.save()
        return requirement

    def create_autosend(self, item, template_type, **kwargs):
        autosend = None
        if isinstance(item, Product):
            (autosend, created) = ProductAutosend.objects.get_or_create(
                product=item, template_type=template_type, **kwargs
            )
        elif isinstance(item, Visit):
            if 'inherit' not in kwargs:
                kwargs['inherit'] = False
            (autosend, created) = VisitAutosend.objects.get_or_create(
                visit=item, template_type=template_type, **kwargs
            )
        if autosend:
            autosend.enabled = True
            autosend.save()
        return autosend

    def get_emails_grouped(self):
        emails = {}
        for email in KUEmailMessage.objects.all():
            key = str(email.template_key)
            if key not in emails:
                emails[key] = []
            sub = emails[key]
            sub.append(email)
        return emails
