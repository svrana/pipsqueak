#!/usr/bin/env python

import os
import unittest

from pipsqueak.main import (
    parse_requirements_file,
    _parse_requirement,
)
from pipsqueak.test.util import (
    req_file,
    default_desc,
)


class TestParse(unittest.TestCase):
    desc = None

    def setUp(self):
        pass

    def test_e_git_egg(self):
        repo_link = "git+git://github.com/ContextLogic/wheezy-captcha.git#egg=wheezy.captcha"
        self.desc = _parse_requirement("-e {}".format(repo_link))
        self.assertEqual(self.desc, default_desc(
            project_name="wheezy.captcha",
            editable=True,
            link=repo_link,
            version_control=dict(
                type="git",
                protocol="git",
                location="git://github.com/ContextLogic/wheezy-captcha.git",
                version=None,
            ),
        ))

    def test_cannonical_1(self):
        self.desc = _parse_requirement("pymongo==2.8")
        self.assertEqual(self.desc, default_desc(
            type="pypi",
            project_name="pymongo",
            specifiers="==2.8",
        ))

    def test_two_versions(self):
        repo_link = "git+git://github.com/svrana/pipsqueak.git@7f9405aaf3935aa4569a803#egg=pipsqueak== 0.1.0"
        self.desc = _parse_requirement(repo_link)
        self.assertEqual(self.desc, default_desc(
            project_name="pipsqueak",
            link=repo_link,
            version_control=dict(
                type="git",
                protocol="git",
                location="git://github.com/svrana/pipsqueak.git",
                version="7f9405aaf3935aa4569a803",
            ),
            specifiers="==0.1.0",
        ))

    def test_from_file(self):
        with req_file("./test_requirements_000.txt", "tornado<=6.0\n"):
            reqs = parse_requirements_file('test_requirements_000.txt')
            self.assertEqual(reqs['tornado'], default_desc(
                type="pypi",
                project_name="tornado",
                source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_000.txt"),
                specifiers="<=6.0",
                line_number=1,
            ))

    def test_from_file_in_file(self):
        with req_file("./test_requirements_001.txt", "   scipy~=0.18.1   \npackage<=1.1\n"):
            with req_file("test_requirements.txt", "-r test_requirements_001.txt"):
                reqs = parse_requirements_file('test_requirements.txt')
                self.assertEqual(reqs['scipy'], default_desc(
                    type="pypi",
                    project_name="scipy",
                    source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                    specifiers="~=0.18.1",
                    line_number=1,
                ))
                self.assertEqual(reqs['package'], default_desc(
                   project_name="package",
                   specifiers="<=1.1",
                   source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                   line_number=2,
               ))

    def test_can_parse(self):
        self.desc = _parse_requirement("backports.shutil-get-terminal-size==1.0.0")
        self.assertEqual(self.desc, default_desc(
            type="pypi",
            project_name="backports.shutil-get-terminal-size",
            specifiers="==1.0.0",
        ))

    def test_can_parse_package_no_version(self):
        self.desc = _parse_requirement("codecov")
        self.assertEqual(self.desc, default_desc(
            type="pypi",
            project_name="codecov",
        ))

    def test_parses_version(self):
        self.desc = _parse_requirement('pytz==2012d')
        self.assertEqual(self.desc, default_desc(
            project_name="pytz",
            specifiers='==2012d',
        ))

if __name__ == '__main__':
    unittest.main()
