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
        self.assertEqual(self.desc['name'], 'wheezy.captcha')
        self.assertEqual(self.desc['location'], "github.com/ContextLogic/wheezy-captcha.git")
        self.assertEqual(self.desc['version'], None)

    def test_git_branch(self):
        _parse_requirement("git+git://github.com/ContextLogic/tornado.git@branch4.5.1#egg=tornado", self.desc)
        self.assertEqual(self.desc, dict(
            type="git",
            name="tornado",
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
            name="pymongo",
            version="2.8",
            location=None,
            attributes=[],
            source=None,
            version_sign="==",
        ))

    def test_from_file(self):
        with req_file("./test_requirements_001.txt", "scipy~=0.18.1"):
            with req_file("test_requirements.txt", "-r test_requirements_001.txt"):
                reqs = parse_requirements_file('test_requirements.txt')
                self.assertEqual(reqs[0], dict(
                    type="pypi",
                    name="scipy",
                    version="0.18.1",
                    location=None,
                    attributes=[],
                    source=os.path.join(os.path.abspath(os.path.curdir), "test_requirements_001.txt"),
                    version_sign="~=",
                ))


if __name__ == '__main__':
    unittest.main()
