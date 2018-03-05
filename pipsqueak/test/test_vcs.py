import unittest

from pipsqueak.main import (
    _parse_requirement,
)
from pipsqueak.test.util import default_desc


class TestVcs(unittest.TestCase):
    desc = None

    def test_can_parse_svn(self):
        repo_link = "svn+http://myrepo/svn/MyApp#egg=MyApp"
        self.desc = _parse_requirement(repo_link)
        self.assertEqual(self.desc, default_desc(
            project_name="MyApp",
            type="version_control",
            link=repo_link,
            version_control=dict(
                type='svn',
                protocol='http',
                location="http://myrepo/svn/MyApp",
                version=None,
            ),
        ))

    def test_can_parse_mercurial(self):
        repo_link = "hg+https://myrepo/hg/MyApp#egg=MyApp"
        self.desc = _parse_requirement(repo_link)
        self.assertEqual(self.desc, default_desc(
            project_name="MyApp",
            type="version_control",
            link=repo_link,
            version_control=dict(
                type="hg",
                protocol="https",
                location="https://myrepo/hg/MyApp",
                version=None,
            ),
        ))

    def test_git_branch(self):
        repo_link = "git+git://github.com/tornadoweb/tornado.git@branch4.5.1#egg=tornado"
        self.desc = _parse_requirement(repo_link)
        self.assertEqual(self.desc, default_desc(
            project_name="tornado",
            type="version_control",
            link=repo_link,
            version_control=dict(
                type="git",
                protocol="git",
                location="git://github.com/tornadoweb/tornado.git",
                version="branch4.5.1",
            ),
        ))
