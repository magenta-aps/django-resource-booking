import backports.unittest_mock
backports.unittest_mock.install()
from unittest.mock import patch


class TestMixin(object):

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
