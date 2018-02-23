"""Exceptions used throughout package"""
from __future__ import absolute_import


class PipsqueakError(Exception):
    """Base pipsqueak exception"""


class ConfigurationError(PipsqueakError):
    """General exception in configuration"""


class RequirementsFileParseError(ConfigurationError):
    """Raised when a general error occurs parsing a requirements file line."""


class RequirementParseError(ConfigurationError):
    """Raised when a general error occurs parsing a requirement. """


class BadCommand(PipsqueakError):
    """Raised when virtualenv or a command is not found"""


class CommandError(PipsqueakError):
    """Raised when there is an error in command-line arguments"""


class InvalidWheelFilename(ConfigurationError):
    """Invalid wheel filename."""
