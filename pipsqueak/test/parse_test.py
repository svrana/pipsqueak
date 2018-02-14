#!/usr/bin/env python

from contextlib import contextmanager
import os
import unittest
from pipsqueak.main import (
    new_descriptor,
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
        self.desc = new_descriptor(None)

    def test_e_git_egg(self):
        _parse_requirement("-e git://github.com/ContextLogic/wheezy-captcha.git#egg=wheezy.captcha", self.desc)
        self.assertEqual(self.desc['type'], 'git')
        self.assertEqual(self.desc['project_name'], 'wheezy.captcha')
        self.assertEqual(self.desc['location'], "github.com/ContextLogic/wheezy-captcha.git")
        self.assertEqual(self.desc['version'], None)

    def test_git_branch(self):
        _parse_requirement("git+git://github.com/ContextLogic/tornado.git@branch4.5.1#egg=tornado", self.desc)
        self.assertEqual(self.desc, dict(
            type="git",
            project_name="tornado",
            version="branch4.5.1",
            location="github.com/ContextLogic/tornado.git",
            attributes=[],
            source=None,
            version_sign=None,
        ))

    def test_cannonical_1(self):
        _parse_requirement("pymongo==2.8", self.desc)
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="pymongo",
            version="2.8",
            location=None,
            attributes=[],
            source=None,
            version_sign="==",
        ))

    def test_two_versions(self):
        _parse_requirement("git+git://github.com/svrana/pipsqueak.git@7f9405aaf3935aa4569a803#egg=pipsqueak== 0.1.0", self.desc)
        self.assertEqual(self.desc, dict(
            type="git",
            project_name="pipsqueak",
            version="0.1.0",
            location="github.com/svrana/pipsqueak.git",
            attributes=[],
            source=None,
            version_sign="==",
        ))

    def test_from_file(self):
        with req_file("./test_requirements_001.txt", "   scipy~=0.18.1   \npackage<=1.1\n"):
            with req_file("test_requirements.txt", "-r test_requirements_001.txt"):
                reqs = parse_requirements_file('test_requirements.txt')
                self.assertEqual(reqs['scipy'], dict(
                    type="pypi",
                    project_name="scipy",
                    version="0.18.1",
                    location=None,
                    attributes=[],
                    source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                    version_sign="~=",
                ))
                self.assertEqual(reqs['package'], dict(
                    type="pypi",
                    project_name="package",
                    version="1.1",
                    location=None,
                    attributes=[],
                    source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                    version_sign="<=",
                ))

    def test_can_parse(self):
        _parse_requirement("backports.shutil-get-terminal-size==1.0.0", self.desc)
        self.assertEqual(self.desc, dict(
            type="pypi",
            project_name="backports.shutil-get-terminal-size",
            version="1.0.0",
            location=None,
            attributes=[],
            source=None,
            version_sign="==",
        ))


if __name__ == '__main__':
    unittest.main()
