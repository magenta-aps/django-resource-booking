# encoding: utf-8
import copy
import math
import re
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import TestCase
from django.utils.datastructures import MultiValueDict
from django.utils.datetime_safe import datetime
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
from booking.models import SurveyXactEvaluationGuest
from booking.models import KUEmailRecipient
from booking.models import Visit
from booking.models import ResourceType
from booking.models import KUEmailMessage
from booking.models import Locality
from booking.models import OrganizationalUnit
from booking.models import OrganizationalUnitType
from booking.models import Product
from booking.models import RoomResponsible
from booking.models import School
from booking.models import Subject
from booking.utils import flatten
from profile.models import UserRole
from resource_booking.tests.mixins import TestMixin, ParsedNode


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
                'success': ["This is a title", u"Blåbærgrød", 'x'*80],
                'fail': [None, '', 'x'*81]
            },
            'teaser': {
                'success': ["This is a teaser", u"Æblegrød", 'x'*300],
                'fail': [None, '', 'x'*301]
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
                'success': [30, 10, 3, 0],
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

    def test_display_product_ui__STUDENT_FOR_A_DAY(self):
        self._test_display_product_ui(
            Product.STUDENT_FOR_A_DAY,
            StudentForADayForm
        )

    def test_display_product_ui__STUDIEPRAKTIK(self):
        self._test_display_product_ui(
            Product.STUDIEPRAKTIK,
            InternshipForm
        )

    def test_display_product_ui__OPEN_HOUSE(self):
        self._test_display_product_ui(
            Product.OPEN_HOUSE,
            OpenHouseForm
        )

    def test_display_product_ui__TEACHER_EVENT(self):
        self._test_display_product_ui(
            Product.TEACHER_EVENT,
            TeacherProductForm
        )

    def test_display_product_ui__GROUP_VISIT(self):
        self._test_display_product_ui(
            Product.GROUP_VISIT,
            ClassProductForm
        )

    def test_display_product_ui__STUDY_PROJECT(self):
        self._test_display_product_ui(
            Product.STUDY_PROJECT,
            StudyProjectForm
        )

    def test_display_product_ui__ASSIGNMENT_HELP(self):
        self._test_display_product_ui(
            Product.ASSIGNMENT_HELP,
            AssignmentHelpForm
        )

    def _test_display_product_ui(self, product_type, form_class):
        data = {}
        fields = {
            key: copy.deepcopy(value)
            for key, value in self.field_definitions.items()
            if key in form_class.Meta.fields
        }
        m2m = {}
        for (key, value) in fields.items():
            if 'success' in value:
                v = self._unpack_success(value['success'], 0, 1)
                if type(v) == list:
                    m2m[key] = v
                else:
                    data[key] = v
        map = Product.time_mode_choice_map
        data['time_mode'] = Product.TIME_MODE_SPECIFIC \
            if Product.TIME_MODE_SPECIFIC in map[product_type] \
            else list(map[product_type])[0]
        data['state'] = Product.ACTIVE

        product = Product(type=product_type, **data)
        product.save()
        for key, value in m2m.items():
            for v in value:
                getattr(product, key).add(v)

        start = datetime.utcnow()+timedelta(days=10)
        end = start+timedelta(hours=1)

        visit = None
        if data['time_mode'] == Product.TIME_MODE_SPECIFIC:
            visit = self.create_visit(
                product=product,
                start=start,
                end=end,
                workflow_status=Visit.WORKFLOW_STATUS_BEING_PLANNED
            )

        response = self.client.get("/product/%d" % product.id)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        self.assertEquals([
                u'Du er her:',
                u'Søgning',
                u"Tilbud #%d - %s" % (product.id, product.title)
            ], flatten([
                ParsedNode._get_text_nodes(el)
                for el in query("ol.breadcrumb")
            ]
        ))
        title_element = query("h1")
        self.assertEquals(product.title, title_element.text())
        self.assertEquals(product.teaser, title_element.next().text())
        self.assertEquals(
            product.description, title_element.next().next().text()
        )

        expected_data = {
            'hvad': self._get_choices_label(
                Product.resource_type_choices, product_type
            ),
            u'arrangør': unicode(self.unit.name),
        }
        if 'maximum_number_of_visitors' in data:
            expected_data['antal'] = \
                u"Max. %d" % data['maximum_number_of_visitors']

        if data['time_mode'] == Product.TIME_MODE_SPECIFIC:
            if 'maximum_number_of_visitors' in data:
                expected_number_of_visitors = \
                    u"%d ledige pladser" % data['maximum_number_of_visitors']
            else:
                expected_number_of_visitors = u'ingen begrænsning'
            expected_data[u'hvornår'] = u"%s\n%s" % (
                    visit.eventtime.interval_display,
                    expected_number_of_visitors
            )
        if 'locality' in data:
            expected_data['hvor'] = '\n'.join([
                unicode(getattr(data['locality'], x))
                for x in ['name', 'address_line', 'zip_city']
                if len(x.strip()) > 0
            ])
        options = []
        if data.get('tour_available'):
            options.append(u'Rundvisning')
        if data.get('catering_available'):
            options.append(u'Forplejning')
        if data.get('presentation_available'):
            options.append(u'Oplæg om uddannelse')
        if data.get('custom_available'):
            options.append(data.get('custom_name'))
        if len(options):
            expected_data['mulighed for'] = '\n'.join(options)

        expected_data = {
            unicode(key+":"): value
            for key, value in expected_data.items()
        }

        rightbox_data = {
            key: '\n'.join([v for v in value])
            for key, value in ParsedNode(
                query(".panel-body dl.dl-horizontal")
            ).extract_dl(True).iteritems()
        }
        self.assertDictEqual(expected_data, rightbox_data)

    def test_search(self):
        p1 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.STUDENT_FOR_A_DAY,
            title=u'Title æ studerende for en dag',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        p2 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.STUDIEPRAKTIK,
            title=u'Title æ studiepraktik',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        p3 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.OPEN_HOUSE,
            title=u'Title æ åbent hus',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        p4 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.GROUP_VISIT,
            title=u'Title æ klassebesøg',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        p5 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.TEACHER_EVENT,
            title=u'Title æ tilbud til undervisere',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        p6 = self.create_product(
            unit=self.unit,
            state=Product.ACTIVE,
            product_type=Product.ASSIGNMENT_HELP,
            title=u'Title æ Lektiehjælp',
            teaser=u'Teaser ø',
            description=u'Description å'
        )
        self._test_search_ui([p1, p2, p3, p4, p5, p6], {'q': u'æ'})
        self._test_search_ui([p1, p2, p3, p4, p5, p6], {'q': u'Teaser ø'})
        self._test_search_ui([p1, p2, p3, p4, p5, p6], {'pagesize': 5})
        self._test_search_ui([p1], {'t': Product.STUDENT_FOR_A_DAY})
        self._test_search_ui([p2], {'t': Product.STUDIEPRAKTIK})
        self._test_search_ui([p3], {'t': Product.OPEN_HOUSE})
        self._test_search_ui([p4], {'t': Product.GROUP_VISIT})
        self._test_search_ui([p5], {'t': Product.TEACHER_EVENT})
        self._test_search_ui([p6], {'t': Product.ASSIGNMENT_HELP})
        self._test_search_ui(
            [p1, p2, p3], {'t': [
                Product.STUDENT_FOR_A_DAY,
                Product.STUDIEPRAKTIK,
                Product.OPEN_HOUSE
            ]}
        )

    def _test_search_ui(self, products, query_params):
        q = QueryDict('', True)
        q.update(MultiValueDict({
            key: self._ensure_list(value)
            for key, value in query_params.items()
        }))
        products_by_id = {product.id: product for product in products}
        pagesize = query_params.get('pagesize', 10)
        expected_pages = int(math.ceil(float(len(products)) / float(pagesize)))
        for page in range(1, expected_pages+1):
            expected_products = products[(page-1)*pagesize:page*pagesize]
            q['page'] = page
            response = self.client.get("/search?%s" % q.urlencode())
            self.assertEquals(200, response.status_code)
            query = pq(response.content)
            self.assertEquals(
                u"%d resultater matcher din søgning på \"%s\""
                % (len(products), query_params.get('q', '')),
                query("h3.results-header").text()
            )
            list_items = query("ul.media-list > li")
            self.assertEquals(len(expected_products), len(list_items))
            found_ids = set()

            # Check list of results, for each entry, find the entry's product
            for list_item in list_items:
                q_list_item = query(list_item)
                product = None
                for link in q_list_item.find("h3.media-heading a"):
                    href = link.get("href")
                    if href:
                        m = re.search(r"/(\d+)[/?$]", href)
                        product_id = int(m.group(1))
                        if product_id in products_by_id:
                            product = products_by_id[product_id]
                            break
                if product is not None:
                    # Check the data outputted in the entry against the product
                    found_ids.add(product.id)
                    actual = {
                        'type': self._get_choices_key(
                            Product.type_choices,
                            unicode(q_list_item.find(
                                ".media-body > div.small"
                            ).text())
                        ),
                        'title': "\n".join(flatten([
                            ParsedNode._get_text_nodes(node)
                            for node in q_list_item.find("h3.media-heading")
                        ])),
                        'teaser': re.sub(
                            r'\s+', " ",
                            q_list_item.find(".media-body > p")
                            .text().strip(u"\u2026 \n")
                        )
                    }
                    expected = {key: getattr(product, key) for key in actual}
                    self.assertDictEqual(expected, actual, q_list_item)
            expected_ids = set([p.id for p in expected_products])
            self.assertSetEqual(
                expected_ids, found_ids,
                "Search result mismatch: Resulting list of products does not "
                "match expected list. Found: %s, expected: %s"
                % (found_ids, expected_ids)
            )

            # Check facet counts
            for (choices, attribute, container_ref) in [
                (School.type_choices, 'institution_level', 'div.education'),
                (Product.resource_type_choices, 'type', 'div.type')
            ]:
                counts = {}
                for key, label in choices:
                    filter = {attribute: key}
                    if 't' in query_params and attribute != 'type':
                        filter['type__in'] = \
                            self._ensure_list(query_params['t'])
                    counts[key] = Product.objects.filter(**filter).count()

                labels = query("%s .checkbox label" % container_ref)
                for label in labels:
                    text = ParsedNode._get_text_nodes(label)
                    key = self._get_choices_key(choices, text[0])
                    count = counts.get(key, 0)
                    if count > 0:
                        self.assertEquals(u"(%d)" % count, text[1])
                    else:
                        self.assertEquals(1, len(text))

    def test_potential_teacher(self):
        UserRole.create_defaults()
        ResourceType.create_defaults()
        user = self.create_default_teacher(unit=self.unit)
        product = self.create_product(
            unit=self.unit,
            potential_teachers=[user],
            time_mode=Product.TIME_MODE_SPECIFIC
        )
        self.assertTrue(
            user.id in [u.id for u in product.potential_teachers.all()]
        )
        self._test_is_present_on_profile(user, product)
        product.delete()

        product = self.create_product(
            unit=self.unit,
            time_mode=Product.TIME_MODE_RESOURCE_CONTROLLED
        )
        self.assertFalse(
            user.id in [u.id for u in product.potential_teachers.all()]
        )
        pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_TEACHER,
            self.unit,
            'test_pool',
            user.userprofile.get_resource()
        )
        self.create_resourcerequirement(product, pool, 1)
        self.assertTrue(
            user.id in [u.id for u in product.potential_teachers.all()]
        )
        self._test_is_present_on_profile(user, product)

    def test_potential_host(self):
        UserRole.create_defaults()
        ResourceType.create_defaults()
        user = self.create_default_host(unit=self.unit)
        product = self.create_product(
            unit=self.unit,
            potential_hosts=[user],
            time_mode=Product.TIME_MODE_SPECIFIC
        )
        self.assertTrue(
            user.id in [u.id for u in product.potential_hosts.all()]
        )
        self._test_is_present_on_profile(user, product)
        product.delete()

        product = self.create_product(
            unit=self.unit,
            time_mode=Product.TIME_MODE_RESOURCE_CONTROLLED
        )
        self.assertFalse(
            user.id in [u.id for u in product.potential_hosts.all()]
        )
        pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_HOST,
            self.unit,
            'test_pool',
            user.userprofile.get_resource()
        )
        self.create_resourcerequirement(product, pool, 1)
        self.assertTrue(
            user.id in [u.id for u in product.potential_hosts.all()]
        )
        self._test_is_present_on_profile(user, product)

    def _test_is_present_on_profile(self, user, product):
        url = "/profile/"
        self.login(url, user)
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        items = query("h3.panel-title")\
            .closest(".panel").find(".panel-body .list-group-item")
        self.assertEquals(1, len(items))
        item = items[0]
        self.assertEquals(product.title, pq(item).find("h2").text())

    def test_evaluation(self):
        EmailTemplateType.set_defaults()
        template1 = self.create_emailtemplate(
            key=EmailTemplateType.NOTIFY_GUEST__EVALUATION_FIRST,
            unit=self.unit,
            subject="Test evaluation",
            body="This is a test. "
                 "Link: {{ recipient.guest.evaluationguest_teacher.link }}"
        )

        product = self.create_product(
            unit=self.unit,
            time_mode=Product.TIME_MODE_SPECIFIC
        )
        evaluation = self.create_evaluation(product, surveyId=12345)
        visit = self.create_visit(
            product,
            start=datetime.now() + timedelta(days=3),
            end=datetime.now() + timedelta(days=3, hours=1)
        )
        self.create_autosend(visit, template1.type)
        booking = self.create_booking(visit, self.create_guest())
        evaluation.save()
        self.set_visit_workflow_status(visit, Visit.WORKFLOW_STATUS_PLANNED)
        # Let visit "expire", so status changes to "executed"
        # and messages are sent out
        count_before = KUEmailMessage.objects.count()
        visit.on_expire()

        self.assertEquals(1, KUEmailMessage.objects.count() - count_before)
        message = KUEmailMessage.objects.last()
        self.assertIsNotNone(message)
        self.assertEquals("Test evaluation", message.subject.strip())
        self.assertTrue(message.body.strip().startswith("This is a test"))
        self.assertEquals(
            "\"%s\" <%s>" % (booking.booker.get_full_name(),
                             booking.booker.email),
            message.recipients
        )

        m = re.search("Link: http://fokusku.dk/e/(.*)", message.body.strip())
        self.assertIsNotNone(m)
        shortlink_id = m.group(1)
        evalguest = SurveyXactEvaluationGuest.objects.get(
            shortlink_id=shortlink_id,
        )
        self.assertEquals(evaluation, evalguest.evaluation)
        self.assertDictEqual(
            {u'opl\xe6g': 0, u'l\xe6rere': 0, u'undvm1': '', u'type1': 0,
             u'ID': product.id, u'skole_id': None, u'antal': None,
             u'rundvis': 0, u'akt1': u'testproduct', u'niveau': None,
             u'oenhed1': None, u'region': None, u'elever': 0,
             u'g\xe6st': u'Tester Testerson', u'enhed1': self.unit.id,
             u'postnr': None, u'undvn1': '', u'skole': None,
             u'tid': visit.start_datetime.strftime('%Y.%m.%d %H:%M:%S'),
             u'email': u'test@example.com'},
            evalguest.get_surveyxact_data()
        )

    def test_email_recipients(self):
        # setup products with users in different roles
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

        products = []

        for product_type, label in Product.resource_type_choices:
            for time_mode in [
                Product.TIME_MODE_NONE, Product.TIME_MODE_SPECIFIC,
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
                products.append(product)

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
            #  products.append(product)

        expected = {
            EmailTemplateType.NOTIFY_EDITORS__BOOKING_CREATED: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator)
            ],
            EmailTemplateType.NOTIFY_HOST__REQ_TEACHER_VOLUNTEER: [
                (KUEmailRecipient.TYPE_TEACHER, teacher)
            ],
            EmailTemplateType.NOTIFY_HOST__REQ_HOST_VOLUNTEER: [
                (KUEmailRecipient.TYPE_HOST, host)
            ],
            EmailTemplateType.NOTIFY_HOST__REQ_ROOM: [
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy)
            ],
            EmailTemplateType.NOTIFY_ALL__BOOKING_COMPLETE: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy)
            ],
            EmailTemplateType.NOTIFY_ALL__BOOKING_CANCELED: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy)
            ],
            EmailTemplateType.NOTITY_ALL__BOOKING_REMINDER: [
                (KUEmailRecipient.TYPE_PRODUCT_RESPONSIBLE, coordinator),
                (KUEmailRecipient.TYPE_ROOM_RESPONSIBLE, roomguy)
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

        for product in products:
            for template_type_key, expected_recipients in expected.iteritems():
                actual_recipients = product.get_recipients(
                    EmailTemplateType.get(template_type_key)
                )
                self.assertEquals(
                    len(expected_recipients), len(actual_recipients),
                    "Expected number of recipients not "
                    "matching for template type %d" % template_type_key
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

    def test_front_page(self):
        # create several products with bookings
        # test that the products show up on the front page
        products = []
        for i in range(1, 6):
            product = self.create_product(
                unit=self.unit,
                title="test %d" % i,
                time_mode=Product.TIME_MODE_SPECIFIC,
                state=Product.ACTIVE
            )
            start = datetime.now() + timedelta(days=10 + i)
            visit = self.create_visit(
                product,
                start,
                start + timedelta(hours=1),
                Visit.WORKFLOW_STATUS_BEING_PLANNED
            )
            product.ensure_statistics()
            products.append(product)
            booking = self.create_booking(visit, self.create_guest())
            booking.ensure_statistics()

        self.assertEquals(
            products,
            list(Product.objects.filter_public_bookable())
        )

        rproducts = products[:]
        rproducts.reverse()
        response = self.client.get("/")
        query = pq(response.content)
        lists = query(".listcontainer > div")

        self._check_frontpage_product_list(
            query,
            query(lists[0]).find(".list-group-item"),
            rproducts
        )
        self._check_frontpage_product_list(
            query,
            query(lists[1]).find(".list-group-item"),
            rproducts
        )

    def _check_frontpage_product_list(self, query, elements, products):
        for i, product in enumerate(products):
            item = query(elements[i])
            self.assertEquals(
                "/product/%d" % product.id,
                item.find("a")[0].get('href')
            )
            itemdata = ParsedNode(item.find("ul")).extract_ul()
            self.assertGreater(len(itemdata), 0)
            self.assertEqual(
                "Type: %s" %
                self._get_choices_label(Product.type_choices, product.type),
                re.sub(r"\s+", ' ', itemdata[0]['text'].strip())
            )
            self.assertEqual(
                "Dato/tid: %s" %
                product.eventtime_set.first().interval_display,
                re.sub(r"\s+", ' ', itemdata[1]['text'].strip())
            )
