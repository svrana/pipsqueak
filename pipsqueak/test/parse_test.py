#!/usr/bin/env python

from contextlib import contextmanager
import os
import unittest
from pipsqueak.main import (
    parse_requirements_file,
    _parse_requirement,
)

@contextmanager
def req_file(filename, contents):
    with open(filename, 'w') as file:
        file.write(contents)
    yield
    os.unlink(filename)


class TestParse(unittest.TestCase):
    desc = None

    def setUp(self):
        pass

    def test_e_git_egg(self):
        self.desc = _parse_requirement("-e git://github.com/ContextLogic/wheezy-captcha.git#egg=wheezy.captcha")
        self.assertEqual(self.desc['type'], 'git')
        self.assertEqual(self.desc['project_name'], 'wheezy.captcha')
        self.assertEqual(self.desc['location'], "git://github.com/ContextLogic/wheezy-captcha.git")
        self.assertEqual(self.desc['editable'], True)

    def test_git_branch(self):
        self.desc = _parse_requirement("git+git://github.com/ContextLogic/tornado.git@branch4.5.1#egg=tornado")
        self.assertEqual(self.desc, dict(
            type="git",
            project_name="tornado",
            version="branch4.5.1",
            location="git://github.com/ContextLogic/tornado.git@branch4.5.1",
            editable=False,
            source=None,
            specifiers=None,
            line_number=None,
        ))

    def test_cannonical_1(self):
        self.desc = _parse_requirement("pymongo==2.8")
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="pymongo",
            specifiers="==2.8",
            location=None,
            editable=False,
            source=None,
            version=None,
            line_number=None,
        ))

    def test_two_versions(self):
        self.desc = _parse_requirement("git+git://github.com/svrana/pipsqueak.git@7f9405aaf3935aa4569a803#egg=pipsqueak== 0.1.0")
        self.assertEqual(self.desc, dict(
            type="git",
            project_name="pipsqueak",
            version="7f9405aaf3935aa4569a803",
            location="git://github.com/svrana/pipsqueak.git@7f9405aaf3935aa4569a803",
            editable=False,
            source=None,
            specifiers="==0.1.0",
            line_number=None,
        ))

    def test_from_file(self):
        with req_file("./test_requirements_000.txt", "tornado<=6.0\n"):
            reqs = parse_requirements_file('test_requirements_000.txt')
            self.assertEqual(reqs['tornado'], dict(
                type="pypi",
                project_name="tornado",
                version=None,
                location=None,
                editable=False,
                source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_000.txt"),
                specifiers="<=6.0",
                line_number=1,
            ))

    def test_from_file_in_file(self):
        with req_file("./test_requirements_001.txt", "   scipy~=0.18.1   \npackage<=1.1\n"):
            with req_file("test_requirements.txt", "-r test_requirements_001.txt"):
                reqs = parse_requirements_file('test_requirements.txt')
                self.assertEqual(reqs['scipy'], dict(
                    type="pypi",
                    project_name="scipy",
                    version=None,
                    location=None,
                    editable=False,
                    source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                    specifiers="~=0.18.1",
                    line_number=1,
                ))
                self.assertEqual(reqs['package'], dict(
                   type="pypi",
                   project_name="package",
                   specifiers="<=1.1",
                   version=None,
                   location=None,
                   editable=False,
                   source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                   line_number=2,
               ))

    def test_can_parse(self):
        self.desc = _parse_requirement("backports.shutil-get-terminal-size==1.0.0")
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="backports.shutil-get-terminal-size",
            location=None,
            source=None,
            specifiers="==1.0.0",
            editable=False,
            version=None,
            line_number=None,
        ))

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

    def test_can_parse_package_no_version(self):
        self.desc = _parse_requirement("codecov")
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="codecov",
            version=None,
            location=None,
            source=None,
            editable=False,
            specifiers=None,
            line_number=None,
        ))

    # def test_malformed_from_file(self):
    #     with req_file("./test_requirements_003.txt", "scipy(=0.18.1"):
    #         pass



if __name__ == '__main__':
    unittest.main()
