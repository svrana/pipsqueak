import unittest

from pipsqueak.main import (
    _parse_requirement,
)


class TestVcs(unittest.TestCase):
    desc = None

    def test_can_parse_svn(self):
        self.desc = _parse_requirement("svn+http://myrepo/svn/MyApp#egg=MyApp")
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="MyApp",
            source=None,
            location="http://myrepo/svn/MyApp",
            specifiers=None,
            editable=False,
            version=None,
            line_number=None,
        ))

    def test_can_parse_mercurial(self):
        self.desc = _parse_requirement("hg+https://myrepo/hg/MyApp#egg=MyApp")
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="MyApp",
            location="https://myrepo/hg/MyApp",
            source=None,
            specifiers=None,
            editable=False,
            version=None,
            line_number=None,
        ))

    def test_git_branch(self):
        self.desc = _parse_requirement("git+git://github.com/tornadoweb/tornado.git@branch4.5.1#egg=tornado")
        self.assertEqual(self.desc, dict(
            type="git",
            project_name="tornado",
            version="branch4.5.1",
            location="git://github.com/tornadoweb/tornado.git@branch4.5.1",
            editable=False,
            source=None,
            specifiers=None,
            line_number=None,
        ))
