"""Stuff that differs in different Python versions and platform
distributions."""
from __future__ import absolute_import, division

import os


def samefile(file1, file2):
    """Provide an alternative for os.path.samefile on Windows/Python2"""
    if hasattr(os.path, 'samefile'):
        return os.path.samefile(file1, file2)
    else:
        path1 = os.path.normcase(os.path.abspath(file1))
        path2 = os.path.normcase(os.path.abspath(file2))
        return path1 == path2

def console_to_str(readline):
    return readline
