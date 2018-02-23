import unittest
from pipsqueak.test.util import req_file

from pipsqueak.exceptions import RequirementParseError
from pipsqueak.main import (
    parse_requirements_file,
)


class TestError(unittest.TestCase):
    def test_malformed_spec_from_file(self):
        with req_file("./test_requirements_003.txt", "scipy(=0.18.1"):
            self.assertRaises(RequirementParseError, parse_requirements_file, 'test_requirements_003.txt')

    def test_invalid_directory_from_file(self):
        with req_file("./test_requirements_004.txt", "/invalid/directory/name"):
            self.assertRaises(RequirementParseError, parse_requirements_file, 'test_requirements_004.txt')

if __name__ == '__main__':
    unittest.main()
