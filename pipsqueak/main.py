import argparse
from collections import defaultdict
import logging
import json
import os.path
import shlex

from packaging.specifiers import (
    Specifier,
    InvalidSpecifier,
    LegacySpecifier,
)
from packaging.utils import canonicalize_name
import pkg_resources

from pipsqueak.options import break_args_options, build_parser
from pipsqueak.pip.freeze import FrozenRequirement
from pipsqueak.pip.vcs import vcs
from pipsqueak.pip.util import get_used_vcs_backend
from pipsqueak.pip.req_install import InstallRequirement


logger = logging.getLogger(__file__)

def _new_descriptor():
    desc = dict(
        editable=False,
        project_name=None,
        type=None,
        source=None,
        line_number=None,
        specifiers=None,
        version_control=None,
    )
    return desc

def _fill_type(req, desc):
    if req.link:
        link = req.link
        for backend in vcs.backends:
            if link.scheme in backend.schemes:
                location, version = backend(str(link)).get_url_rev()
                if '+' in link.scheme:
                    protocol = link.scheme.split('+')[1]
                else:
                    protocol = link.scheme

                desc['type'] = 'version_control'
                desc['version_control'] = dict(
                    type=backend.name,
                    protocol=protocol,
                    location=location,
                    version=version,
                )
                return

        if "file://" in str(link):
            desc['type'] = 'file'
            return
    else:
        desc['type'] = 'pypi' # need a better descriptor for this

def _grab_location(req):
    link = req.link
    if link:
        vc = get_used_vcs_backend(link)
        if vc:
            return vc.get_url_rev()[0]
    return None

def _ireq_to_desc(ireq):
    desc = _new_descriptor()

    _fill_type(ireq, desc)
    desc['project_name'] = ireq.name
    desc['editable'] = ireq.editable
    desc['specifiers'] = str(ireq.specifier) if ireq.specifier else None
    desc['source'] = None
    desc['line_number'] = None
    if ireq.comes_from:
        desc['source'] = ireq.comes_from.split(':')[0]
        desc['line_number'] = int(ireq.comes_from.split(':')[1])

    return desc

def _parse_requirement(req):
    reqset = {}
    _process_line(req, reqset)
    desc = _ireq_to_desc(reqset[reqset.keys()[0]])
    return desc

def _add_ireq(reqset, ireq):
    reqset[canonicalize_name(ireq.name)] = ireq

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
        _add_ireq(reqset, ireq)
    elif opts.editables:
        ireq = InstallRequirement.from_editable(
            opts.editables[0],
            comes_from=comes_from
        )
        _add_ireq(reqset, ireq)
    elif opts.requirements:
        ireqs = _parse_requirements_file(opts.requirements[0])
        for ireq in ireqs.itervalues():
            _add_ireq(reqset, ireq)
    else:
        raise Exception("Failed to process requirement", line)

def _yield_lines(strs):
    """ Yield non-empty/non-comment lines with their line numbers. """
    for lineno, line in enumerate(strs):
        line = line.strip()
        if line and not line.startswith('#'):
            yield lineno+1, line

def _parse_requirements_iterable(reqs, source=None):
    reqset = {}

    for lineno, line in _yield_lines(reqs):
        _process_line(line, reqset, source=source, lineno=lineno)

    return reqset

def _parse_requirements_file(requirements):
    requirements = os.path.abspath(requirements)
    if not os.path.exists(requirements):
        raise Exception("Could not locate requirements file %s", requirements)

    with open(requirements) as reqs:
        return _parse_requirements_iterable(reqs, source=requirements)

def parse_requirements_file(requirements):
    reqs = _parse_requirements_file(requirements)
    return {canonicalize_name(k):_ireq_to_desc(v)
            for k,v in reqs.iteritems()}

def _get_installed_packages():
    installations = {}

    for dist in pkg_resources.working_set:
        try:
            req = FrozenRequirement.from_dist(dist, [])
        except Exception:
            logger.warning(
                "Could not parse requirement: %s",
                dist.project_name
            )
            continue

        installations[req.name] = req

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
        '--file',
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
    installed = _get_installed_packages()
    reqs = [ str(dist.req) for dist in installed.itervalues() ]
    required = _parse_requirements_iterable(reqs)
    return required, installed

def report(requirements):
    required = parse_requirements_file(requirements)
    for _, details in required.iteritems():
        details['source'] = None

    installed, unused = parse_installed()
    installed = { k:_ireq_to_desc(v) for k,v in installed.iteritems() }

    diff = defaultdict(lambda: defaultdict(dict))

    for name, details in required.iteritems():
        if name not in installed:
            if details['specifiers']:
                diff[name]['specifiers'] = details['specifiers']
            if details['version_control']:
                diff[name]['version'] = details['version_control']['version']
            diff[name]['installed'] = 'false'
            continue

        if installed[name] != details:
            if installed[name]['type'] != details['type']:
                diff[name]['type']['installed'] = installed[name]['type']
                diff[name]['type']['required'] = details['type']

            installed_vc = installed[name]['version_control']
            required_vc = details['version_control']
            if installed_vc and required_vc and installed_vc != required_vc:
                diff[name]['version_control'] = defaultdict(lambda: defaultdict(dict))

                if installed_vc.get('type') != required_vc.get('type'):
                    diff[name]['version_control']['type']['installed'] = installed_vc.get('type') #if installed_vc.get('type')
                    diff[name]['version_control']['type']['required'] = required_vc.get('type') #if required_vc.get('type')
                if installed_vc.get('version') != required_vc.get('version'):
                    diff[name]['version_control']['version']['installed'] = installed_vc.get('version') #if installed_vc.get('version')
                    diff[name]['version_control']['version']['required'] = required_vc.get('version') #if required_vc.get('version')

            if installed[name]['specifiers'] != details['specifiers']:
                if not _versions_match(details['specifiers'], installed[name]['specifiers']):
                    diff[name]['specifiers']['installed'] = installed[name]['specifiers']
                    diff[name]['specifiers']['required'] = details['specifiers']

    return diff

def main():
    ap = argparse.ArgumentParser(description='Parse and compare python dependencies')
    ap.add_argument('command', choices=['report'])
    ap.add_argument('args', nargs=argparse.REMAINDER)
    args = ap.parse_args()

    return _command_line_report(args.args)

if __name__ == '__main__':
    main()
