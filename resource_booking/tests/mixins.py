from datetime import timedelta

import backports.unittest_mock
import pytz
from django.contrib.auth.models import User
from django.db.models import Model
from django.utils.datetime_safe import datetime

from booking.models import Booking
from booking.models import EmailTemplate
from booking.models import EmailTemplateType
from booking.models import EventTime
from booking.models import Guest
from booking.models import KUEmailMessage
from booking.models import Locality
from booking.models import Product
from booking.models import ProductAutosend
from booking.models import ResourceType
from booking.models import Room
from booking.models import RoomResponsible
from booking.models import SurveyXactEvaluation
from booking.models import Visit
from booking.models import VisitAutosend
from booking.resource_based.models import ResourcePool
from booking.resource_based.models import ResourceRequirement
from profile.constants import ADMINISTRATOR
from profile.constants import COORDINATOR
from profile.constants import FACULTY_EDITOR
from profile.constants import HOST
from profile.constants import TEACHER
from profile.models import UserRole, UserProfile

backports.unittest_mock.install()  # noqa
from django.test.client import Client

class ParsedNode(object):
    def __init__(self, el):
        self.el = el

    def __str__(self):
        return '\n'.join(TestMixin._get_text_nodes(self.el))

    def __unicode__(self):
        return u'\n'.join(TestMixin._get_text_nodes(self.el))

    def keys(self):
        return ['text'] + (['url'] if self.el.find("a") else [])

    def __getitem__(self, key):
        if key == 'text':
            return TestMixin._get_text_nodes(self.el)
        if key == 'url':
            return self.urls

    @property
    def urls(self):
        return [a.prop("href") for a in self.el.find("a")]


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
        self.client.logout()
        response = self.client.get(url)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/profile/login?next=%s" % url, response['Location'])
        # self.client.login(username="admin", password="admin")
        self.client.force_login(user)

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

    def create_default_locality(
            self, name='test_locality', description='test_description',
            address='test_address', zip_city='9999 testcity',
            unit=None
    ):
        (locality, c) = Locality.objects.get_or_create(
            name=name, description=description,
            address_line=address, zip_city=zip_city, organizationalunit=unit
        )
        return locality

    def create_default_room(
            self, name="test_room", locality=None
    ):
        (room, c) = Room.objects.get_or_create(name=name, locality=locality)
        return room

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

    def create_resourcepool(self, type, unit, name='test_pool', *resources):
        if not isinstance(type, ResourceType):
            type = ResourceType.objects.get(id=type)
        (resourcepool, c) = ResourcePool.objects.get_or_create(
            name=name,
            resource_type=type,
            organizationalunit=unit
        )
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
        else:
            print(item.__class__.__name__)
        if autosend:
            autosend.enabled = True
            autosend.save()
        print("a")
        print(autosend)
        print(item.visitautosend_set.all())
        return autosend

    def create_evaluation(self, product, for_students=False, surveyId=1234):
        (evaluation, created) = SurveyXactEvaluation.objects.get_or_create(
            product=product,
            surveyId=surveyId,
        )
        evaluation.for_students = for_students
        evaluation.for_teachers = not for_students
        evaluation.save()
        return evaluation

    def create_guest(self, firstname="Tester", lastname="Testerson",
                     email="test@example.com", **kwargs):
        defaults = {
            'level': Guest.student,
            'firstname': "Tester",
            'lastname': "Testerson",
            'email': "test@example.com"
        }
        defaults.update(kwargs)
        guest = Guest(**defaults)
        guest.save()
        return guest

    def create_booking(self, visit, guest):
        booking = Booking()
        booking.visit = visit
        booking.booker = guest
        booking.save()
        return booking

    def create_default_roomresponsible(self,
                                       name="RoomTester",
                                       email="room@example.com",
                                       phone=12345678,
                                       unit=None
                                       ):
        (roomresponsible, c) = RoomResponsible.objects.get_or_create(
            name=name, email=email, phone=phone, organizationalunit=unit
        )
        return roomresponsible

    def set_visit_workflow_status(self, visit, *status):
        for s in status:

            if s in [id for (id, label) in visit.possible_status_choices()]:
                visit.workflow_status = s
                visit.save()
            else:
                raise Exception(
                    "Invalid workflow state change for visit:"
                    " %s (%d) => %s (%d)" % (
                        self._get_choices_label(
                            Visit.workflow_status_choices,
                            visit.workflow_status
                        ),
                        visit.workflow_status,
                        self._get_choices_label(
                            Visit.workflow_status_choices,
                            s
                        ), s
                    )
                )

    def get_emails_grouped(self):
        emails = {}
        for email in KUEmailMessage.objects.all():
            key = str(email.template_key)
            if key not in emails:
                emails[key] = []
            sub = emails[key]
            sub.append(email)
        return emails

    @staticmethod
    def _unpack_success(data, list_index, tuple_index):
        if type(data) == list:
            data = data[list_index]
        if type(data) == tuple:
            data = data[tuple_index]
        return data

    @staticmethod
    def _ensure_list(data):
        return data if type(data) == list else [data]

    @staticmethod
    def _apply_value(data, key, value):
        data = data.copy()
        if value is None:
            del data[key]
        else:
            data[key] = value
        return data

    @staticmethod
    def _get_text_nodes(element):
        return [
            unicode(x.strip())
            for x in element.itertext()
            if len(x.strip()) > 0
        ]

    @staticmethod
    def _get_choices_label(choices, value):
        for (v, label) in choices:
            if v == value:
                return label

    @staticmethod
    def _get_choices_key(choices, label):
        for (value, l) in choices:
            if l == label:
                return value

    @staticmethod
    def replace_models_with_pks(data):
        for (key, value) in data.items():
            if isinstance(value, Model):
                data[key] = value.pk
        return data

    @classmethod
    def _node_to_dict(cls, node):
        print(type(node), dir(node))
        d = {"text": node.text}
        if node.tag == 'a':
            d['url'] = node.attr("href")
        children = getattr(node, 'children', None) or (hasattr(node, 'getchildren') and node.getchildren()) or []
        if children:
            d['children'] = [
                cls._node_to_dict(child)
                for child in children
            ]
        return d

    @classmethod
    def extract_dl(cls, dl, text_only=False):
        data = {}
        for item in dl.find("dt"):
            key = unicode(item.text).strip().lower()
            value = []
            for node in item.itersiblings():
                if node.tag != 'dd':
                    break
                # parsednode = ParsedNode(node)
                # value.append(unicode(parsednode) \
                #     if text_only else parsednode)
                # value += cls._get_text_nodes(node)
                value.append(cls._node_to_dict(node))
            data[key] = value
        return data

    @classmethod
    def extract_ul(cls, ul):
        data = []
        for node in ul.find("li"):
            data.append(cls._node_to_dict(node))
        return data

    @classmethod
    def extract_table(cls, table):
        headers = [cell.text for cell in table.find("th, thead td")]
        return [
            {
                # headers[i]: cls._get_text_nodes(cell)
                headers[i]: cls._node_to_dict(cell)
                for (i, cell) in enumerate(table.find("tbody td"))
            }
            for row in table.find("tbody tr")
        ]
