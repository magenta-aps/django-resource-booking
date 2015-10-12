import os

from pep8 import StyleGuide

from django.test import TestCase
from django.conf import settings

# Create your tests here.


def pep8_test(filepath):
    def do_test(self):
        sg = StyleGuide()
        sg.input_dir(filepath)
        output = sg.check_files().get_statistics()
        self.assertEqual(len(output), 0)

    return do_test


def p(filepath):
    return os.path.join(settings.BASE_DIR, filepath)


class PEP8Test(TestCase):
    test_resource = pep8_test(p('resource_booking'))
    test_booking = pep8_test(p('booking'))
