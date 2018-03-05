from contextlib import contextmanager
import os

from pipsqueak.main import _new_descriptor

@contextmanager
def req_file(filename, contents):
    with open(filename, 'w') as file:
        file.write(contents)
    try:
        yield
    finally:
        os.unlink(filename)

def default_desc(**kwargs):
    desc = _new_descriptor()

    if 'version_control' in kwargs:
        desc['type'] = 'version_control'
    else:
        desc['type'] = 'pypi'

    desc.update(**kwargs)
    return desc
