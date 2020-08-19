# encoding: utf-8
import copy
from decimal import Decimal

from django.test import TestCase
from pyquery import PyQuery as pq

from booking.forms import AssignmentHelpForm
from booking.forms import ClassProductForm
from booking.forms import InternshipForm
from booking.forms import OpenHouseForm
from booking.forms import OtherProductForm
from booking.forms import StudentForADayForm
from booking.forms import StudyProjectForm
from booking.forms import TeacherProductForm
from booking.models import EmailTemplateType
from booking.models import Locality
from booking.models import OrganizationalUnit
from booking.models import OrganizationalUnitType
from booking.models import Product
from booking.models import RoomResponsible
from booking.models import School
from booking.models import Subject
from resource_booking.tests.mixins import TestMixin


class TestProduct(TestMixin, TestCase):

    """
    Test creation, display, editing for each type of product
    Test getters
    Test evaluation
    """

    @classmethod
    def setUpClass(cls):
        super(TestProduct, cls).setUpClass()
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

        cls.field_definitions = {
            'title': {
                'success': ["This is a title", u"Blåbærgrød", 'x'*60],
                'fail': [None, '', 'x'*61]
            },
            'teaser': {
                'success': ["This is a teaser", u"Æblegrød", 'x'*210],
                'fail': [None, '', 'x'*211]
            },
            'description': {
                'success': ["This is a description", u"Rødgrød med fløde"],
                'fail': ['', None]
            },
            'price': {
                'success': [
                    0, 1, 500, 10000, Decimal('12.34'),
                    Decimal('1'*8 + '.00'), (None, Decimal(0))
                ],
                'fail': [-1, -500, 'a', '1'*11, Decimal('12.345')]
            },
            'state': {
                'success': [
                    Product.CREATED, Product.ACTIVE, Product.DISCONTINUED
                ],
                'fail': [None, 10, 'x']
            },
            'institution_level': {
                'success': [
                    Subject.SUBJECT_TYPE_GYMNASIE,
                    Subject.SUBJECT_TYPE_GRUNDSKOLE,
                    Subject.SUBJECT_TYPE_BOTH
                ],
                'fail': [None, 10, 'x']
            },
            'minimum_number_of_visitors': {
                'success': [0, 1, 1000, None],
                'fail': [-1, 'a']
            },
            'maximum_number_of_visitors': {
                'success': [1000, 0, 1, None],
                'fail': [-1, 'a']
            },
            'do_create_waiting_list': {
                'success': [('on', True), ('', False)]
            },
            'waiting_list_length': {
                'success': [0, 1, 1000, None],
                'fail': [-1, 'a']
            },
            'waiting_list_deadline_days': {
                'success': [0, 1, 1000, None],
                'fail': [-1, 'a']
            },
            'waiting_list_deadline_hours': {
                'success': [0, 1, 23, None],
                'fail': [-1, 'a', '24', '36']
            },
            'time_mode': {
                'fail': [None, 10, 'x']
            },
            'duration': {
                'success': ['05:00', '00:15', '00:00', None],
                'fail': ['00:01', 'x', 'some random text']
            },
            'locality': {
                'success': [(cls.locality.id, cls.locality)],
                'fail': [5000]
            },
            'tour_available': {
                'success': [('on', True), ('', False)]
            },
            'catering_available': {
                'success': [('on', True), ('', False)]
            },
            'presentation_available': {
                'success': [('on', True), ('', False)]
            },
            'custom_available': {
                'success': [('on', True), ('', False)]
            },
            'custom_name': {
                'success': [
                    'some text', u'Jordbærgrød', None, ('', None), 'x'*50
                ],
                'fail': ['x'*51]
            },
            'tilbudsansvarlig': {
                'success': [(cls.admin.id, cls.admin), None],
                'fail': [5000]
            },
            'roomresponsible': {
                'success': [(cls.roomresponsible.id, [cls.roomresponsible])],
                'fail': [5000, 'a', -1]
            },
            'organizationalunit': {
                'success': (cls.unit.id, cls.unit),
                'fail': [None, '', 'x']
            },
            'preparation_time': {
                'success': [
                    'some text', u'Hindbærgrød', None, ('', None), 'x'*200
                ],
                'fail': 'x'*201
            },
            'comment': {
                'success': ['some text', u'Jordbærgrød', (None, ''), '']
            },
            'only_one_guest_per_visit': {
                'success': [('on', True), ('', False)]
            },
            'booking_close_days_before': {
                'success': [0, 7, 10, 30],
                'fail': [None, -3, 'x']
            },
            'booking_max_days_in_future': {
                'success': [0, 3, 10, 30],
                'fail': [None, -3, 'x']
            },
            'inquire_enabled': {
                'success': [('on', True), ('', False)]
            },
        }

    def test_create_product_ui_type(self):
        self.login("/product/create", self.admin)
        for product_type, label in Product.resource_type_choices:
            response = self.client.post(
                "/product/create",
                {'type': str(product_type)}
            )
            self.assertEquals(302, response.status_code)
            self.assertEquals(
                "/product/create/%d?back=None" % product_type,
                response['Location']
            )
            response = self.client.post(
                "/product/create",
                {'type': str(product_type + 10)}
            )
            self.assertEquals(200, response.status_code)
            query = pq(response.content)
            errors = query("[name=\"type\"]") \
                .closest("div.form-group").find("ul.errorlist li")
            self.assertEquals(1, len(errors))

    def test_create_product_ui__STUDENT_FOR_A_DAY(self):
        self._test_create_product_ui(
            Product.STUDENT_FOR_A_DAY,
            StudentForADayForm
        )

    def test_create_product_ui__STUDIEPRAKTIK(self):
        self._test_create_product_ui(Product.STUDIEPRAKTIK, InternshipForm)

    def test_create_product_ui__OPEN_HOUSE(self):
        self._test_create_product_ui(Product.OPEN_HOUSE, OpenHouseForm)

    def test_create_product_ui__TEACHER_EVENT(self):
        self._test_create_product_ui(Product.TEACHER_EVENT, TeacherProductForm)

    def test_create_product_ui__GROUP_VISIT(self):
        self._test_create_product_ui(Product.GROUP_VISIT, ClassProductForm)

    def test_create_product_ui__STUDY_PROJECT(self):
        self._test_create_product_ui(Product.STUDY_PROJECT, StudyProjectForm)

    def test_create_product_ui__ASSIGNMENT_HELP(self):
        self._test_create_product_ui(
            Product.ASSIGNMENT_HELP,
            AssignmentHelpForm
        )

    def test_create_product_ui__OTHER_OFFERS(self):
        self._test_create_product_ui(Product.OTHER_OFFERS, OtherProductForm)

    def _test_create_product_ui(self, product_type, form_class):

        fields = {
            key: copy.deepcopy(value)
            for key, value in self.field_definitions.items()
            if key in form_class.Meta.fields
        }
        fields['time_mode']['success'] = \
            list(Product.time_mode_choice_map[product_type])
        remain = [
            x for (x, l) in Product.time_mode_choices
            if x not in Product.time_mode_choice_map[product_type]
        ]
        fields['time_mode']['fail'] += remain

        # Fields is a dict mapping field names to dicts,
        # where each sub-dict has a success value
        # (values to pass to the form, and optionally
        # what to expect in the resulting object),
        # and fails to expect errors on.
        url = "/product/create/%d" % product_type
        self.login(url, self.admin)
        form_data = {
            'type': product_type,
            'studymaterial_set-TOTAL_FORMS': 1,
            'studymaterial_set-INITIAL_FORMS': 0,
            'studymaterial_set-MIN_NUM_FORMS': 0,
            'studymaterial_set-MAX_NUM_FORMS': 1000,
            'productautosend_set-TOTAL_FORMS': 14,
            'productautosend_set-INITIAL_FORMS': 0,
            'productautosend_set-MIN_NUM_FORMS': 0,
            'productautosend_set-MAX_NUM_FORMS': 1000
        }
        for (index, templatetype) in \
                enumerate(EmailTemplateType.objects.all()):
            form_data["productautosend_set-%d-template_type" % index] = \
                templatetype.id
            form_data["productautosend_set-%d-days" % index] = ""
            form_data["productautosend_set-%d-product" % index] = ""
            form_data["productautosend_set-%d-enabled" % index] = "on"
            form_data["productautosend_set-%d-autosend_ptr" % index] = ""

        for (key, value) in fields.items():
            if 'success' in value:
                form_data[key] = self._unpack_success(value['success'], 0, 0)

        # Now try each fail (pass fail values to form and expect errors)
        for (key, value) in fields.items():
            if 'fail' in value:
                for submit_value in self._ensure_list(value['fail']):
                    msg = u"Testing with value %s in field %s, " \
                          "expected to fail, did not fail"\
                          % (unicode(submit_value), unicode(key))
                    response = self.client.post(
                        url,
                        self._apply_value(form_data, key, submit_value)
                    )
                    self.assertEquals(200, response.status_code, msg)
                    query = pq(response.content)
                    errors = query("[name=\"%s\"]" % key) \
                        .closest("div.form-group").find("ul.errorlist li")
                    self.assertEquals(1, len(errors), msg)

        # Try success values
        for (key, value) in fields.items():
            if 'success' in value:
                for v in self._ensure_list(value['success']):
                    (submit_value, expected_value) = v\
                        if type(v) == tuple\
                        else (v, v)
                    msg = u"Testing with value %s in field %s, " \
                          "expected to succeed, did not succeed" \
                          % (unicode(submit_value), unicode(key))
                    response = self.client.post(
                        url,
                        self._apply_value(form_data, key, submit_value)
                    )
                    if response.status_code != 302:
                        print(response.content)
                    self.assertEquals(302, response.status_code, msg)
                    product = Product.objects.last()
                    for (otherkey, othervalue) in fields.items():
                        if 'success' in othervalue:
                            if otherkey == key:
                                expected_now = expected_value
                            else:
                                expected_now = self._unpack_success(
                                    othervalue['success'], 0, 1
                                )
                            actual = getattr(product, otherkey)
                            if actual.__class__.__name__ == \
                                    'ManyRelatedManager':
                                actual = list(actual.all())
                            self.assertEquals(expected_now, actual, msg)

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
