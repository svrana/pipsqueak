import argparse
from collections import defaultdict
import json
import os.path
import shlex
from subprocess import Popen, PIPE

from packaging.requirements import Specifier

from pipsqueak.options import break_args_options, build_parser
from pipsqueak.pip.download import get_used_vcs_backend
from pipsqueak.pip.req_install import InstallRequirement


def _new_descriptor():
    desc = dict(
        editable=False,
        project_name=None,
        location=None,
        version=[],
        type=None,
        source=None,
        line_number=None,
        specifiers=None,
    )
    return desc

def _grab_version(req):
    link = req.link
    if link:
        vc = get_used_vcs_backend(link)
        if vc:
            return vc.get_url_rev()[1]
    return None

def _grab_type(req):
    if req.link:
        link = str(req.link)
        if "git://" in link:
            return "git"
        elif "file://" in link:
            return "file"
    return "pypi"

def _grab_location(req):
    link = req.link
    if link:
        link = req.link.url_without_fragment
        if link:
            if '+' in link:
                return link.split('+')[1]
    return link

def _ireq_to_desc(ireq):
    desc = _new_descriptor()

    desc['type'] = _grab_type(ireq)
    desc['project_name'] = ireq.name
    desc['location'] = _grab_location(ireq)
    desc['editable'] = ireq.editable
    desc['specifiers'] = str(ireq.specifier) if ireq.specifier else None
    desc['version'] = _grab_version(ireq)
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
    # todo: catch duplicates
    reqset[ireq.name] = ireq

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
        ireq = InstallRequirement.from_editable(opts.editables[0], comes_from=comes_from)
        _add_ireq(reqset, ireq)
    elif opts.requirements:
        for ireq in _parse_requirements_file(opts.requirements[0]).itervalues():
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
    return { k:_ireq_to_desc(v) for k,v in reqs.iteritems() }

def _get_pip_freeze_output():
    process = Popen(["pip", "freeze", "."], stdout=PIPE)
    output, _ = process.communicate()
    reqs = output.splitlines()
    return reqs

def _versions_match(required, installed):
    if required is None:
        return True

    req = Specifier(required)
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
    reqs = _get_pip_freeze_output()
    required = _parse_requirements_iterable(reqs)
    return required

def report(requirements):
    required = parse_requirements_file(requirements)
    for _, details in required.iteritems():
        details['source'] = None

    installed = parse_installed()
    installed = { k:_ireq_to_desc(v) for k,v in installed.iteritems() }

    diff = defaultdict(lambda: defaultdict(dict))

    for name, details in required.iteritems():
        if name not in installed:
            if details['specifiers']:
                diff[name]['specifiers'] = details['specifiers']
            if details['version']:
                diff[name]['version'] = details['version']
            diff[name]['installed'] = 'false'
            continue

        if installed[name] != details:
            if installed[name]['type'] != details['type']:
                diff[name]['type']['installed'] = installed[name]['type']
                diff[name]['type']['required'] = details['type']
            if installed[name]['location'] != details['location']:
                diff[name]['location']['installed'] = installed[name]['location']
                diff[name]['location']['required'] = details['location']
            if installed[name]['version'] != details['version']:
                diff[name]['version']['installed'] = installed[name]['version']
                diff[name]['version']['required'] = details['version']
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
