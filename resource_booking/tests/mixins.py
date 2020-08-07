import backports.unittest_mock
from django.contrib.auth.models import User

from booking.models import Product
from profile.constants import ADMINISTRATOR, TEACHER, HOST, COORDINATOR, \
    FACULTY_EDITOR
from profile.models import UserRole, UserProfile

backports.unittest_mock.install()
from unittest.mock import patch
from django.test.client import Client

class TestMixin(object):

    admin = None

    def __init__(self, *args, **kwargs):
        super(TestMixin, self).__init__(*args, **kwargs)
        self.client = None

    @classmethod
    def setUpClass(cls):
        super(TestMixin, cls).setUpClass()
        cls.admin = User.objects.create(username="admin", is_superuser=True)
        cls.admin.set_password('admin')
        cls.admin.save()
        (role, created) = UserRole.objects.get_or_create(
            {'name': u"Administrator"},
            role=ADMINISTRATOR
        )
        adminprofile = UserProfile(
            user=cls.admin,
            user_role=role
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

    def create_user(self, username, email, role, first_name=None, last_name=None, unit=None):
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

    def create_default_teacher(self, username="test_teacher", email="test_teacher@example.com", first_name="test", last_name="teacher", unit=None):
        return self.create_user(
            username,
            email,
            TEACHER,
            first_name,
            last_name,
            unit
        )

    def create_default_host(self, username="test_host", email="test_host@example.com", first_name="test", last_name="host", unit=None):
        return self.create_user(
            username,
            email,
            HOST,
            first_name,
            last_name,
            unit
        )

    def create_default_coordinator(self, username="test_coordinator", email="test_coordinator@example.com", first_name="test", last_name="coordinator", unit=None):
        return self.create_user(
            username,
            email,
            COORDINATOR,
            first_name,
            last_name,
            unit
        )

    def create_default_editor(self, username="test_editor", email="test_editor@example.com", first_name="test", last_name="editor", unit=None):
        return self.create_user(
            username,
            email,
            FACULTY_EDITOR,
            first_name,
            last_name,
            unit
        )

    def create_default_product(self, unit=None, time_mode=Product.TIME_MODE_NONE, potential_teachers=None, potential_hosts=None, state=Product.CREATED):
        product = Product(
            title="testproduct",
            teaser="for testing",
            description="this is a test product",
            organizationalunit=unit,
            time_mode=time_mode,
            state=state
        )
        product.save()
        if potential_teachers is not None:
            if type(potential_teachers) != list:
                potential_teachers = [potential_teachers]
            for teacher in potential_teachers:
                product.potentielle_vaerter.add(teacher)
        if potential_hosts is not None:
            if type(potential_hosts) != list:
                potential_hosts = [potential_hosts]
            for host in potential_hosts:
                product.potentielle_vaerter.add(host)
        return product
