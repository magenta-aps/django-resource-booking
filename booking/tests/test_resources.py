from booking.models import OrganizationalUnitType, OrganizationalUnit, Resource
from booking.resource_based.models import ResourceType, ResourcePool
from profile.models import UserRole
from resource_booking.tests.mixins import TestMixin
from django.test import TestCase
from pyquery import PyQuery as pq


class TestResources(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestResources, cls).setUpClass()
        UserRole.create_defaults()
        ResourceType.create_defaults()
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
    """
    Test creation, display, editing, listing, deletion for resources
    Test association with visits
    Test calendar
    Test availability logic
    """
    def test_resource_pool(self):
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
                "/resourcepool/create/%d/%d" % (resource_type.id, self.unit.id),
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


    def test_resource(self):
        self.login("/resource/create", self.admin)

        for resource_type in ResourceType.objects.all():
            response = self.client.post(
                "/resource/create",
                {
                    'type': str(resource_type.id),
                    'unit': self.unit.id
                }
            )
            self.assertEquals(302, response.status_code)
            self.assertEquals(
                "/resource/create/%d/%d" %
                (resource_type.id, self.unit.id),
                response['Location']
            )

            response = self.client.post(
                "/resource/create/%d/%d" %
                (resource_type.id, self.unit.id),
                {'name': ''}
            )
            self.assertEquals(200, response.status_code)
            query = pq(response.content)
            errors = query("[name=\"name\"]") \
                .closest("div.form-group").find("ul.errorlist li")
            self.assertEquals(1, len(errors))

            name = "TestResource_%s" % resource_type.name
            response = self.client.post(
                "/resource/create/%d/%d" % (resource_type.id, self.unit.id),
                {'name': name}
            )
            self.assertEquals(302, response.status_code)
            created = Resource.objects.get(
                organizationalunit=self.unit,
                resource_type=resource_type,
                name=name
            )
            self.assertEquals(
                "/resource/%d" % created.id,
                response['Location']
            )
