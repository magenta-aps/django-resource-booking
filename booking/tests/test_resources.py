# encoding: utf-8
import copy

from django.test import TestCase
from pyquery import PyQuery as pq

from booking.models import OrganizationalUnitType, OrganizationalUnit, \
    TeacherResource, HostResource, RoomResource
from booking.resource_based.forms import EditItemResourceForm, \
    EditVehicleResourceForm
from booking.resource_based.models import ResourceType, ResourcePool
from profile.models import UserRole
from resource_booking.tests.mixins import TestMixin, ParsedNode


class TestResources(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestResources, cls).setUpClass()
        UserRole.create_defaults()
        ResourceType.create_defaults()
        cls.unittype = OrganizationalUnitType.objects.create(name="Fakultet")
        cls.unit = OrganizationalUnit.objects.create(
            name=u"testunit", type=cls.unittype
        )
        cls.admin.userprofile.organizationalunit = cls.unit
        cls.admin.userprofile.save()

        cls.field_definitions = {}
    """
    Test creation, display, editing, listing, deletion for resources
    Test association with visits
    Test calendar
    Test availability logic
    """
    def test_create_resource_pool(self):
        self.login("/resourcepool/create", self.admin)

        for resource_type in ResourceType.objects.all():
            response = self.client.post(
                "/resourcepool/create",
                {
                    'type': str(resource_type.id),
                    'unit': self.unit.id
                }
            )
            self.assertEquals(302, response.status_code)
            self.assertEquals(
                "/resourcepool/create/%d/%d" %
                (resource_type.id, self.unit.id),
                response['Location']
            )

            response = self.client.post(
                "/resourcepool/create/%d/%d" %
                (resource_type.id, self.unit.id),
                {'name': ''}
            )
            self.assertEquals(200, response.status_code)
            query = pq(response.content)
            errors = query("[name=\"name\"]") \
                .closest("div.form-group").find("ul.errorlist li")
            self.assertEquals(1, len(errors))

            name = "TestPool_%s" % resource_type.name
            response = self.client.post(
                "/resourcepool/create/%d/%d" %
                (resource_type.id, self.unit.id),
                {'name': name}
            )
            self.assertEquals(302, response.status_code)
            created = ResourcePool.objects.get(
                organizationalunit=self.unit,
                resource_type=resource_type,
                name=name
            )
            self.assertEquals(
                "/resourcepool/%d" % created.id,
                response['Location']
            )

    def test_display_resource_pool(self):
        room = self.create_default_room(
            locality=self.create_default_locality(unit=self.unit)
        )
        pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_ROOM,
            self.unit,
            'test_pool',
            room.resource
        )
        url = "/resourcepool/%d" % pool.id
        self.login(url, self.admin)
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        headers = query("h1")
        self.assertEquals(1, len(headers))
        self.assertEquals(pool.name, headers[0].text)
        data = ParsedNode(query("dl")).extract_dl(True)
        self.assertDictEqual(
            {
                u'medlemmer': [room.name],
                u'anvendes af': [u'Ingen tilbud'],
                u'type': [
                    ResourceType.objects.get(
                        id=ResourceType.RESOURCE_TYPE_ROOM
                    ).name
                ],
                u'enhed': [self.unit.name],
                u'navn': [pool.name]
            },

            data
        )

    def test_list_resource_pool(self):
        room = self.create_default_room(
            locality=self.create_default_locality(unit=self.unit)
        )
        pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_ROOM,
            self.unit,
            'test_pool',
            room.resource
        )
        url = '/resourcepool/'
        self.login(url, self.admin)
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        data = ParsedNode(query("table")).extract_table()
        self.assertEquals(1, len(data))
        self.assertEquals([{
            'Navn': {
                'text': 'test_pool',
                'children': [{
                    'text': 'test_pool',
                    'url': "/resourcepool/%d" % pool.id
                }]
            },
            'Antal medlemmer': {'text': '1'},
            'Type': {'text': 'Lokale'},
            'Enhed': {'text': 'testunit'},
            'Handling': {
                'text': u'Redigér\n\nSlet',
                'children': [
                    {
                        'url': "/resourcepool/%d/edit?back=/resourcepool/" %
                               pool.id,
                        'text': u'Redig\xe9r'
                    },
                    {
                        'url': "/resourcepool/%d/delete?back=/resourcepool/" %
                               pool.id,
                        'text': 'Slet'
                    }
                ]
            }
        }], data)

    def test_create_resource_ui_ITEM(self):
        locality = self.create_default_locality(unit=self.unit)
        self._test_create_resource_ui(
            ResourceType.RESOURCE_TYPE_ITEM,
            EditItemResourceForm,
            name={'success': 'testitem', 'fail': [None, '']},
            locality={'success': [locality, None]}
        )

    def test_create_resource_ui_VEHICLE(self):
        locality = self.create_default_locality(unit=self.unit)
        self._test_create_resource_ui(
            ResourceType.RESOURCE_TYPE_VEHICLE,
            EditVehicleResourceForm,
            name={'success': 'testitem', 'fail': [None, '']},
            locality={'success': [locality, None]}
        )

    def test_create_resource_TEACHER(self):
        user = self.create_default_teacher(
            username="TestTeacher", unit=self.unit
        )
        resources = list(TeacherResource.objects.filter(user=user))
        self.assertEquals(1, len(resources))
        resource = resources[0]
        self.assertEquals(user, resource.user)
        self.assertEquals(self.unit, resource.organizationalunit)

    def test_create_resource_HOST(self):
        user = self.create_default_host(username="TestHost", unit=self.unit)
        resources = list(HostResource.objects.filter(user=user))
        self.assertEquals(1, len(resources))
        resource = resources[0]
        self.assertEquals(user, resource.user)
        self.assertEquals(self.unit, resource.organizationalunit)

    def test_create_resource_ROOM(self):
        room = self.create_default_room(
            locality=self.create_default_locality(unit=self.unit)
        )
        resources = list(RoomResource.objects.filter(room=room))
        self.assertEquals(1, len(resources))
        resource = resources[0]
        self.assertEquals(room, resource.room)

    def _test_create_resource_ui(
            self, resource_type_id, form_class, **form_extra
    ):
        resource_type = ResourceType.objects.get(id=resource_type_id)
        self.login("/resource/create", self.admin)

        fields = {
            key: copy.deepcopy(value)
            for key, value in self.field_definitions.items()
            if key in form_class.Meta.fields
        }
        fields.update(form_extra)

        response = self.client.post(
            "/resource/create",
            {
                'type': str(resource_type.id),
                'unit': self.unit.id
            }
        )

        url = "/resource/create/%d/%d" % (resource_type.id, self.unit.id)
        self.assertEquals(302, response.status_code)
        self.assertEquals(url, response['Location'])

        form_data = {
            'type': resource_type,
        }
        for (key, value) in fields.items():
            if 'success' in value:
                form_data[key] = self._unpack_success(value['success'], 0, 0)

        # Now try each fail (pass fail values to form and expect errors)
        for (key, value) in fields.items():
            if 'fail' in value:
                for submit_value in self._ensure_list(value['fail']):
                    msg = u"Testing with value %s in field %s, " \
                          "expected to fail, did not fail" \
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
                    (submit_value, expected_value) = v \
                        if type(v) == tuple \
                        else (v, v)
                    msg = u"Testing with value %s in field %s, " \
                          "expected to succeed, did not succeed" \
                          % (unicode(submit_value), unicode(key))
                    data = self._apply_value(form_data, key, submit_value)
                    self.replace_models_with_pks(data)
                    response = self.client.post(
                        url,
                        data
                    )
                    self.assertEquals(302, response.status_code, msg)
                    resource = resource_type.resource_class.objects.last()
                    for (otherkey, othervalue) in fields.items():
                        if 'success' in othervalue:
                            if otherkey == key:
                                expected_now = expected_value
                            else:
                                expected_now = self._unpack_success(
                                    othervalue['success'], 0, 1
                                )
                            actual = getattr(resource, otherkey)
                            if actual.__class__.__name__ == \
                                    'ManyRelatedManager':
                                actual = list(actual.all())
                            self.assertEquals(expected_now, actual, msg)

    def test_display_resource(self):
        room = self.create_default_room(
            locality=self.create_default_locality(unit=self.unit)
        )
        resource = room.resource
        pool = self.create_resourcepool(
            ResourceType.RESOURCE_TYPE_ROOM,
            self.unit,
            'test_pool',
            resource
        )
        url = "/resource/%d" % resource.id
        self.login(url, self.admin)
        response = self.client.get(url)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        headers = query("h1")
        self.assertEquals(1, len(headers))
        self.assertEquals(room.name, headers[0].text)
        self.assertDictEqual(
            {
                u'grupper': [pool.name],
                u'type': [resource.resource_type.name],
                u'enhed': [self.unit.name],
                u'navn': [room.name]
            },
            ParsedNode(query("dl")).extract_dl(True)
        )

    def test_product_calendar(self):
        # create product
        # create calendar for product
        # add calendar time
        # test calendar ui
        # test calendar navigation
        # test calendar time editing
        pass

    def test_resource_occupied(self):
        # create resource with calendar
        # create product with visit
        # make the resource unavailable at a specific timerange
        # test that the resource cannot be assigned to the
        # visit due to being unavailable
        pass
