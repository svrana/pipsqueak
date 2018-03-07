import argparse
from collections import defaultdict
import logging
import json
import os.path
import shlex
from multiprocessing import Pool

from packaging.specifiers import (
    Specifier,
    InvalidSpecifier,
    LegacySpecifier,
)
from packaging.utils import canonicalize_name
import pkg_resources

from pipsqueak.exceptions import ConfigurationError, InvalidFieldError
from pipsqueak.options import break_args_options, build_parser
from pipsqueak.pip.freeze import FrozenRequirement
from pipsqueak.pip.vcs import vcs
from pipsqueak.pip.util import get_used_vcs_backend, is_file_url
from pipsqueak.pip.req_install import InstallRequirement


stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
stream_handler.setFormatter(formatter)
root_logger = logging.getLogger('')
root_logger.addHandler(stream_handler)
logger = logging.getLogger(__file__)


class PipReq(object):
    def __init__(self, **kwargs):
        self.editable = False
        self.project_name = None
        self.type = None
        self.source = None
        self.line_number = None
        self.specifiers = None
        self.version_control = None
        self.link = None
        self.ireq = None
        self.update(**kwargs)

    def update(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k not in self.__dict__:
                raise InvalidFieldError("{} is not a valid field".format(k))
            setattr(self, k, v)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.iteritems()
                if k not in ['link']}

    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return repr(self.__dict__)

    @classmethod
    def from_ireq(cls, req):
        """ Factory method for PipReq construction given an
        InstallRequirement.
        """
        if req.comes_from:
            source = req.comes_from.split(':')[0]
            line_number = int(req.comes_from.split(':')[1])
        else:
            source = None
            line_number = None

        if req.link:
            vcs_backend = get_used_vcs_backend(req.link)
            if vcs_backend:
                location, version = vcs_backend.get_url_rev()
                if '+' in req.link.scheme:
                    protocol = req.link.scheme.split('+')[1]
                else:
                    protocol = req.link.scheme

                link = req.link.url
                type = 'version_control'
                version_control = dict(
                    type=vcs_backend.name,
                    protocol=protocol,
                    location=location,
                    version=version,
                )
            elif is_file_url(req.link.url):
                type = 'file'
        else:
            link = None
            version_control = None
            type = 'pypi'

        specifiers = str(req.specifier) if req.specifier else None
        return cls(
            project_name=req.name,
            type=type,
            editable=req.editable,
            specifiers=specifiers,
            source=source,
            line_number=line_number,
            version_control=version_control,
            link=link,
        )


class IReqSet(object):
    """ A collection of InstallRequirements """
    def __init__(self):
        self.reqset = dict()

    def add(self, ireq):
        # TODO: Don't allow dupes unless they are the same
        name = canonicalize_name(ireq.name)
        self.reqset[name] = ireq

    def itervalues(self):
        return self.reqset.itervalues()

    def iteritems(self):
        return self.reqset.iteritems()

    def _first(self):
        return self.reqset[self.reqset.keys()[0]]

    def to_dict(self):
        return self.reqset

    def to_pipreq_dict(self):
        return {k: PipReq.from_ireq(v) for k, v in self.reqset.iteritems()}


def _parse_requirement(req):
    """ This was used to bootstrap testing and not used.. """
    reqset = IReqSet()
    _process_line(req, reqset)
    pipreq = PipReq.from_ireq(reqset._first())
    return pipreq


def _process_line(line, reqset, source=None, lineno=None):
    parser = build_parser(line)
    defaults = parser.get_default_values()
    args_str, options_str = break_args_options(line)
    opts, _ = parser.parse_args(shlex.split(options_str), defaults)

    if source:
        comes_from = "%s:%s" % (source, lineno)
    else:
        comes_from = None

    if args_str:
        ireq = InstallRequirement.from_line(args_str, comes_from=comes_from)
        reqset.add(ireq)
    elif opts.editables:
        ireq = InstallRequirement.from_editable(
            opts.editables[0],
            comes_from=comes_from
        )
        reqset.add(ireq)
    elif opts.requirements:
        ireqs = _parse_requirements_file(opts.requirements[0])
        for ireq in ireqs.itervalues():
            reqset.add(ireq)
    else:
        raise Exception("Failed to process requirement", line)


def _yield_lines(strs):
    """ Yield non-empty/non-comment lines with their line numbers. """
    for lineno, line in enumerate(strs):
        line = line.strip()
        if line and not line.startswith('#'):
            yield lineno+1, line


def _parse_requirements_iterable(reqs, source=None):
    reqset = IReqSet()

    for lineno, line in _yield_lines(reqs):
        _process_line(line, reqset, source=source, lineno=lineno)

    return reqset


def _parse_requirements_file(requirements):
    requirements = os.path.abspath(requirements)
    if not os.path.exists(requirements):
        raise ConfigurationError("Could not locate requirements file %s",
                                 requirements)

    with open(requirements) as reqs:
        return _parse_requirements_iterable(reqs, source=requirements)


def parse_requirements_file(requirements):
    """ Parse the pip requirements file specified by requirements.

    Return a dictionary from package name to PipReq.
    """
    reqset = _parse_requirements_file(requirements)
    return reqset.to_pipreq_dict()


def _get_installed_as_dist():
    installed = {}
    # pylint: disable=E1133
    for p in pkg_resources.working_set:
        installed[canonicalize_name(p.project_name)] = p
    return installed


def _get_installed_as_frozen_reqs():
    installations = {}

    for name, dist in _get_installed_as_dist().iteritems():
        try:
            req = FrozenRequirement.from_dist(dist, [])
        except Exception:
            logger.warning(
                "Could not parse requirement: %s",
                dist.project_name
            )
            continue
        installations[name] = req

    return installations


def _versions_match(required, installed):
    if required is None:
        return True

    try:
        req = Specifier(required)
    except InvalidSpecifier:
        req = LegacySpecifier(required)

    contains = req.contains(installed[2:])
    return contains


def _command_line_report(args):
    ap = argparse.ArgumentParser(
        description='Parse and manipulate pip dependencies'
    )
    ap.add_argument(
        '--file', '-f',
        type=str,
        default='requirements.txt',
        help='pip-requirements file',
    )
    ap.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        help='No output, only return value'
    )
    args = ap.parse_args(args)
    filename = os.path.abspath(args.file)
    if not os.path.exists(filename):
        print "Could not locate %s" % filename
        return 1
    diff = report(filename)
    if not args.quiet:
        print json.dumps(diff, indent=4)
    return len(diff)


def parse_installed():
    # TODO: We keep the frozenreq around b/c it has the disk location and
    # we can easily turn it into a Requirement. Add as_requirement and
    # from_dist methods to PipReq and store location when created from dist.
    # to PipReq and store location, i.e., from_dist() Or just store the dist
    # too.
    installed_frozen = _get_installed_as_frozen_reqs()
    reqs = [str(dist.req) for dist in installed_frozen.itervalues()]
    installed_reqs = _parse_requirements_iterable(reqs)
    return installed_reqs, installed_frozen


def _compare_versions(installed, required, dist):
    diff = {}
    installed_vc = installed.version_control
    backend_cls = vcs.get_backend(installed_vc['type'])

    installed_backend = backend_cls(dist.req)
    required_backend = backend_cls(required.link)
    url, url_rev = required_backend.get_url_rev()

    if not installed_backend.check_destination(dist.location, url):
        diff = defaultdict(lambda: defaultdict(dict))
        diff['location']['installed'] = installed_backend.get_url(dist)
        diff['location']['required'] = dist.location
        return dict(diff)

    rev_options = required_backend.make_rev_options(url_rev)
    if installed_backend.is_commit_id_equal(dist.location, rev_options.rev):
        return diff

    installed_rev = installed_backend.get_revision(dist.location)
    upstream_rev = installed_backend.get_latest_revision(url, rev_options.rev)
    if installed_rev == upstream_rev:
        return diff

    diff = defaultdict(lambda: defaultdict(dict))
    diff['version']['installed'] = installed_rev
    diff['version']['required'] = upstream_rev

    # convert to dict for pickling that occurs during multiprocessing
    return dict(diff)


def _grab_vc_version_info(installed, required, frozen):
    diff = defaultdict(lambda: defaultdict(dict))

    check = []
    for name, _ in required.iteritems():
        if name not in installed:
            continue
        installed_vc = installed[name].version_control
        required_vc = installed[name].version_control
        if (installed_vc and required_vc and
                installed_vc['type'] == required_vc['type']):
            check.append(name)

    pool = Pool()
    for name in check:
        diff[name] = pool.apply_async(
            _compare_versions,
            (installed[name], required[name], frozen[name])
        )
    pool.close()
    pool.join()

    consume = {name: obj.get() for name, obj in diff.iteritems() if obj.get()}
    return consume


def report(requirements):
    required = parse_requirements_file(requirements)
    for _, details in required.iteritems():
        details.source = None

    installed, installed_frozen = parse_installed()
    installed = installed.to_pipreq_dict()

    version_info = _grab_vc_version_info(installed, required, installed_frozen)

    diff = defaultdict(lambda: defaultdict(dict))

    for name, details in required.iteritems():
        if name not in installed:
            if details.specifiers:
                diff[name]['specifiers'] = details.specifiers
            if details.version_control:
                diff[name]['version'] = details.version_control['version']
            diff[name]['installed'] = 'false'
            continue

        if installed[name] != details.to_dict():
            installed_vc = installed[name].version_control
            required_vc = details.version_control
            if installed_vc and required_vc:
                if installed_vc != required_vc:
                    if installed_vc.get('type') != required_vc.get('type'):
                        vc = diff[name]['version_control'] = defaultdict(
                            lambda: defaultdict(dict)
                        )
                        vc['type']['installed'] = installed_vc['type']
                        vc['type']['required'] = required_vc.get['type']
                    else:
                        if name in version_info:
                            diff[name]['version_control'] = version_info[name]
            elif ((installed_vc and not required_vc) or
                  (not installed_vc and required_vc)):
                vc = diff[name]['version_control'] = defaultdict(
                    lambda: defaultdict(dict)
                )
                if installed_vc:
                    vc['type']['installed'] = installed_vc['type']
                if required_vc:
                    vc['type']['required'] = required_vc['type']

            required_specs = details.specifiers
            installed_specs = installed[name].specifiers
            if installed_specs != required_specs:
                if not _versions_match(required_specs, installed_specs):
                    diff[name]['specifiers']['installed'] = installed_specs
                    diff[name]['specifiers']['required'] = required_specs

    return diff


def main():
    ap = argparse.ArgumentParser(
        description='Parse and compare python dependencies'
    )
    ap.add_argument('--logging', choices=['info', 'warn', 'debug'],
                    help='log level', default='info')
    ap.add_argument('command', choices=['report'])
    ap.add_argument('args', nargs=argparse.REMAINDER)
    args = ap.parse_args()

    logger.setLevel(args.logging.upper())

    return _command_line_report(args.args)


if __name__ == '__main__':
    main()
