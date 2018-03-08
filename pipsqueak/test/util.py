from contextlib import contextmanager
import os

from pipsqueak.main import _process_line, PipReq, IReqSet


@contextmanager
def req_file(filename, contents):
    with open(filename, 'w') as file:
        file.write(contents)
    try:
        yield
    finally:
        os.unlink(filename)


def default_desc(**kwargs):
    desc = PipReq()

    if 'version_control' in kwargs:
        desc.type = 'version_control'
    else:
        desc.type = 'pypi'

    desc.update(**kwargs)
    return desc


def _parse_requirement(req):
    reqset = IReqSet()
    _process_line(req, reqset)
    pipreq = PipReq.from_ireq(reqset._first())
    return pipreq
