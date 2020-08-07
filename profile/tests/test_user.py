# encoding: utf-8
import re

from django.contrib.auth.models import User
from django.test import TestCase
from pyquery import PyQuery as pq

from booking.models import OrganizationalUnit, OrganizationalUnitType, Product
from booking.resource_based.models import ResourceType
from profile.constants import TEACHER, HOST, FACULTY_EDITOR, COORDINATOR
from profile.models import UserRole
from resource_booking.tests.mixins import TestMixin


class TestUser(TestMixin, TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestUser, cls).setUpClass()
        UserRole.create_defaults()
        ResourceType.create_defaults()
        cls.unittype = OrganizationalUnitType.objects.create(name="Fakultet")
        cls.unit = OrganizationalUnit.objects.create(name="testunit", type=cls.unittype)
        cls.admin.userprofile.organizationalunit = cls.unit
        cls.admin.userprofile.save()

    def test_user_create_code(self):
        user = self.create_user(
            username="tester",
            first_name="test",
            last_name="testersen",
            email="test@example.com",
            role=TEACHER
        )
        self.assertEqual("tester", str(user.userprofile))
        self.assertEqual("\"test testersen\" <test@example.com>", user.userprofile.get_full_email())
        self.assertEqual(TEACHER, user.userprofile.get_role())
        self.assertEqual("Underviser", user.userprofile.get_role_name())
        self.assertFalse(user.userprofile.can_create())
        self.assertFalse(user.userprofile.is_host)
        self.assertTrue(user.userprofile.is_teacher)
        self.assertFalse(user.userprofile.is_coordinator)
        self.assertFalse(user.userprofile.is_faculty_editor)
        self.assertFalse(user.userprofile.is_administrator)

    def test_user_create_ui(self):
        self.login("/profile/user/create", self.admin)
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'test',
            'last_name': 'testersen',
            'password1': '12345',
            'password2': '12345',
            'role': str(UserRole.objects.get(role=TEACHER).id),
            'organizationalunit': str(self.unit.id)
        }
        fields = {
            'username': None,
            'email': None,
            'password1': None,
            'password2': [None, "different_password"],
            'role': [None, "1234"],
            'organizationalunit': [None, "1234"]
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
                response = self.client.post("/profile/user/create", data)
                self.assertEquals(200, response.status_code)
                query = pq(response.content)
                errors = query("[name=\"%s\"]" % key).closest("div.form-group").find("ul.errorlist li")
                self.assertEquals(1, len(errors))

        response = self.client.post("/profile/user/create", form_data)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/profile/users", response['Location'])

    def test_user_list_ui(self):
        self.login("/profile/users", self.admin)
        user = self.create_default_teacher(unit=self.unit)
        list = self.client.get("/profile/users?role=%d" % TEACHER)
        self.assertTemplateUsed(list, "profile/user_list.html")
        self.assertInHTML(
            '<a href="/profile/user/create" class="btn btn-primary btn-sm">'
            '<span class="glyphicon glyphicon-plus" aria-hidden="true"></span>'
            'Opret ny bruger'
            '</a>',
            list.content
        )
        query = pq(list.content)
        items = query("ul.list-unstyled li")
        self.assertEquals(1, len(items))
        found = {}
        for i in items.find("div.row"):
            label = query(i).find("div.userlist-label")
            value = label.next()
            found[re.sub(r"\W", "", label.text().lower())] = value.text()
        self.assertDictEqual(
            {
                'brugernavn': user.username,
                'navn': user.get_full_name(),
                'email': user.email,
                'enhed': user.userprofile.organizationalunit.name,
                'rolle': user.userprofile.user_role.name
            },
            found
        )

        list = self.client.get("/profile/users?unit=%d" % (self.unit.id+1))
        query = pq(list.content)
        items = query("ul.list-unstyled li")
        self.assertEquals(0, len(items))

        list = self.client.get("/profile/users?role=6")
        query = pq(list.content)
        items = query("ul.list-unstyled li")
        self.assertEquals(0, len(items))

        list = self.client.get("/profile/users?q=nouser")
        query = pq(list.content)
        items = query("ul.list-unstyled li")
        self.assertEquals(0, len(items))

        for name in [user.username, user.first_name, user.last_name]:
            for i in range(1, len(name)):
                list = self.client.get("/profile/users?q=%s" % name[0:i])
                query = pq(list.content)
                items = query("ul.list-unstyled li")
                self.assertEquals(1, len(items))

    def test_user_edit_ui(self):
        user = self.create_default_teacher(unit=self.unit)
        self.login("/profile/user/%d" % user.id, self.admin)
        form_data = {
            'username': 'changed_testuser',
            'email': 'changed_test@example.com',
            'first_name': 'changed_test',
            'last_name': 'changed_testersen',
            'password1': 'changed_12345',
            'password2': 'changed_12345',
            'role': str(UserRole.objects.get(role=HOST).id),
            'organizationalunit': str(self.unit.id)
        }
        fields = {
            'username': None,
            'email': None,
            'password2': [None, "different_password"],
            'role': [None, "1234"],
            'organizationalunit': [None, "1234"]
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
                response = self.client.post("/profile/user/%d" % user.id, data)
                self.assertEquals(200, response.status_code)
                query = pq(response.content)
                errors = query("[name=\"%s\"]" % key).closest("div.form-group").find("ul.errorlist li")
                self.assertEquals(1, len(errors))

        response = self.client.post("/profile/user/%d" % user.id, form_data)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/profile/users", response['Location'])

    def test_user_delete_ui(self):
        user = self.create_default_teacher(unit=self.unit)
        self.login("/profile/user/%d/delete" % user.id, self.admin)
        response = self.client.get("/profile/user/%d/delete" % user.id)
        self.assertEquals(200, response.status_code)
        query = pq(response.content)
        items = query("input[type=\"submit\"]")
        self.assertEquals(1, len(items))
        self.assertEquals(1, User.objects.filter(username=user.username).count())

        response = self.client.post("/profile/user/%d/delete" % user.id)
        self.assertEquals(302, response.status_code)
        self.assertEquals("/profile/users", response['Location'])
        self.assertEquals(0, User.objects.filter(username=user.username).count())

    def test_profile_capabilities(self):
        teacher = self.create_default_teacher(unit=self.unit)
        host = self.create_default_host(unit=self.unit)
        coordinator = self.create_default_coordinator(unit=self.unit)
        editor = self.create_default_editor(unit=self.unit)
        other_editor = self.create_default_editor(
            username="test_editor2",
            unit=OrganizationalUnit.objects.create(name="testunit2", type=self.unittype)
        )
        product = self.create_default_product(
            unit=self.unit,
            time_mode=Product.TIME_MODE_SPECIFIC,
            potential_teachers=teacher,
            potential_hosts=host
        )
        self.assertEquals(TEACHER, teacher.userprofile.get_role())
        self.assertEquals(HOST, host.userprofile.get_role())
        self.assertEquals(COORDINATOR, coordinator.userprofile.get_role())
        self.assertEquals(FACULTY_EDITOR, editor.userprofile.get_role())

        self.assertTrue(teacher.userprofile.is_teacher)
        self.assertTrue(host.userprofile.is_host)
        self.assertTrue(coordinator.userprofile.is_coordinator)
        self.assertTrue(editor.userprofile.is_faculty_editor)
        self.assertTrue(self.admin.userprofile.is_administrator)

        self.assertFalse(teacher.userprofile.can_notify(product))
        self.assertFalse(host.userprofile.can_notify(product))
        self.assertTrue(coordinator.userprofile.can_notify(product))
        self.assertTrue(editor.userprofile.can_notify(product))
        self.assertFalse(other_editor.userprofile.can_notify(product))
        self.assertTrue(self.admin.userprofile.can_notify(product))

        self.assertFalse(teacher.userprofile.can_edit(product))
        self.assertFalse(host.userprofile.can_edit(product))
        self.assertTrue(coordinator.userprofile.can_edit(product))
        self.assertTrue(editor.userprofile.can_edit(product))
        self.assertFalse(other_editor.userprofile.can_edit(product))
        self.assertTrue(self.admin.userprofile.can_edit(product))

        self.assertFalse(teacher.userprofile.unit_access(self.unit))
        self.assertFalse(host.userprofile.unit_access(self.unit))
        self.assertTrue(coordinator.userprofile.unit_access(self.unit))
        self.assertTrue(editor.userprofile.unit_access(self.unit))
        self.assertFalse(other_editor.userprofile.unit_access(self.unit))
        self.assertTrue(self.admin.userprofile.unit_access(self.unit))

        self.assertFalse(teacher.userprofile.can_edit_product())
        self.assertFalse(host.userprofile.can_edit_product())
        self.assertFalse(coordinator.userprofile.can_edit_product())
        self.assertTrue(editor.userprofile.can_edit_product())
        self.assertTrue(other_editor.userprofile.can_edit_product())
        self.assertTrue(self.admin.userprofile.can_edit_product())

        self.assertFalse(teacher.userprofile.can_edit_visit())
        self.assertFalse(host.userprofile.can_edit_visit())
        self.assertFalse(coordinator.userprofile.can_edit_visit())
        self.assertTrue(editor.userprofile.can_edit_visit())
        self.assertTrue(self.admin.userprofile.can_edit_visit())

        self.assertEquals(self.unit, teacher.userprofile.get_faculty())
        self.assertEquals(self.unit, host.userprofile.get_faculty())
        self.assertEquals(self.unit, coordinator.userprofile.get_faculty())
        self.assertEquals(self.unit, editor.userprofile.get_faculty())
        self.assertEquals(self.unit, self.admin.userprofile.get_faculty())

        self.assertListEqual([self.admin], list(teacher.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(host.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(coordinator.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(editor.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(self.admin.userprofile.get_admins()))

        self.assertListEqual([self.admin], list(teacher.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(host.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(coordinator.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(editor.userprofile.get_admins()))
        self.assertListEqual([self.admin], list(self.admin.userprofile.get_admins()))
