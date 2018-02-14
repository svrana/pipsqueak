import argparse
from collections import defaultdict
import json
import os.path
import re
from subprocess import Popen, PIPE


PACKAGE_MATCH = r"[\w|\-\.]+"
PYPI_MATCH= r"(%s)\s*(\W\W)\s*([\w|\W]+)" % PACKAGE_MATCH

def new_descriptor(source_filename):
    desc = dict(
        attributes=[],
        project_name=None,
        location=None,
        version=[],
        type=None,
        source=source_filename,
        version_sign=None
    )
    return desc

def _grab_project_name(req):
    if "egg=" in req:
        egg_start = req.index("egg=") + len("egg=")
        match = re.match(PYPI_MATCH, req[egg_start:])
        if match:
            return match.group(1)
        else:
            return req[egg_start:]
    elif req[0] != '-':
        match = re.match(PYPI_MATCH, req)
        if not match:
            match = re.match(PACKAGE_MATCH, req)
            if match:
                return req
            else:
                raise Exception("Could not identify package name in '%s'", req)
        return match.group(1)
    return None

def _grab_version(req):
    start_loc = None

    if '@' in req and '==' not in req:
        # req contains both commit and version id--
        #   pip seems to ignore the commit and use the version in this case,
        start_loc = req.index('@') + 1
    else:
        match = re.match(PYPI_MATCH, req)
        if match:
            return match.group(3)
        elif '==' in req:
            start_loc = req.index("==") + 2
            match = re.match(PYPI_MATCH, req[start_loc:])
            if match:
                return match.group(3)
        else:
            return None

    while start_loc < len(req):
        if req[start_loc] == ' ':
            start_loc += 1
        else:
            break

    version = req[start_loc:]
    if '#' in version:
        version = version[0:version.index('#')]

    return version

def _grab_version_sign(req):
    match = re.match(PYPI_MATCH, req)
    if match:
        return match.group(2)
    elif 'egg=' in req:
        start_loc = req.index("egg=") + len("egg=")
        match = re.match(PYPI_MATCH, req[start_loc:])
        if match:
            return match.group(2)

    return None

def _grab_location(req):
    if '@' in req:
        end_loc = req.index('@')
    elif '#' in req:
        end_loc = req.index('#')
    else:
        return None

    try:
        start_loc = req.index("://") + len("://")
        return req[start_loc:end_loc]
    except:
        import pdb ; pdb.set_trace()

def _grab_type(req):
    if "git://" in req:
        return "git"
    elif "file://" in req:
        return "file"
    return "pypi"

def _parse_requirement(req, desc):
    desc['type'] = _grab_type(req)
    desc['project_name'] = _grab_project_name(req)
    desc['location'] = _grab_location(req)
    desc['version'] = _grab_version(req)
    desc['version_sign'] = _grab_version_sign(req)

    return desc

def _parse_requirement_line(requirements_filename, req):
    required = {}

    desc = new_descriptor(requirements_filename)

    if req.startswith("-r"):
        match = re.match(r"-r \s*([\w\W]+)\s*", req)
        if not match:
            raise Exception("Could not parse requirement line: %s", req)
        filename = match.group(1)
        moredeps = parse_requirements_file(filename)
        # TODO: check for duplicates with different specs
        for k,v in moredeps.iteritems():
            required[k] = v
    else:
        _parse_requirement(req, desc)
        required[desc['project_name']] = desc

    return required

def parse_requirements(reqs):
    required = {}

    for line in reqs:
        line = line.lstrip().rstrip()
        modules = _parse_requirement_line(None, line)
        for k,v in modules.iteritems():
            required[k] = v

    return required

def _set_source(reqs, source):
    for _, details in reqs.iteritems():
        # ones that are loaded from a sub requirment will have their
        # source specified already
        if details['source'] is None:
            details['source'] = source

    return reqs

def parse_requirements_file(requirements):
    requirements = os.path.abspath(requirements)
    if not os.path.exists(requirements):
        raise Exception("Could not locate requirements file %s", requirements)

    with open(requirements) as reqs:
        modules = parse_requirements(reqs)
        _set_source(modules, requirements)
        return modules

def _get_pip_freeze_output():
    process = Popen(["pip", "freeze", "."], stdout=PIPE)
    output, _ = process.communicate()
    reqs = [line for line in output.split('\n') if line]
    return reqs

def parse_installed():
    reqs = _get_pip_freeze_output()
    required = parse_requirements(reqs)
    return required

def report(requirements):
    required = parse_requirements_file(requirements)
    for _, details in required.iteritems():
        details['source'] = None

    installed = parse_installed()
    for _, details in installed.iteritems():
        details['source'] = None

    diff = defaultdict(lambda: defaultdict(dict))

    for name, details in required.iteritems():
        if name not in installed:
            diff[name]['installed'] = 'false'

        if installed[name] != details:
            if installed[name]['type'] != details['type']:
                diff[name]['type']['installed'] = installed[name]['type']
                diff[name]['type']['required'] = details['type']
            if installed[name]['location'] != details['location']:
                diff[name]['location']['installed'] = installed[name]['location']
                diff[name]['location']['required'] = details['location']
            if installed[name]['attributes'] != details['attributes']:
                diff[name]['attributes']['installed'] = installed[name]['attributes']
                diff[name]['attributes']['required'] = details['attributes']
            if details['version'] == None:
                continue
            if installed[name]['version'] != details['version']:
                diff[name]['version']['installed'] = installed[name]['version']
                diff[name]['version']['required'] = details['version']
            if installed['version_sign'] != details['version_sign']:
                diff[name]['version_sign']['installed'] = installed[name]['version_sign']
                diff[name]['version_sign']['required'] = details['version_sign']

    return diff

def command_line_report(args):
    ap = argparse.ArgumentParser(
        description='Parse and manipulate pip dependencies'
    )
    ap.add_argument(
        '--file',
        type=str,
        default='requirements.txt',
        help='pip-requirements file',
    )
    args = ap.parse_args(args)

    filename = os.path.abspath(args.file)
    if not os.path.exists(filename):
        print "Could not locate %s" % filename
        return 1

    diff = report(filename)
    print json.dumps(diff, indent=4)

def main():
    ap = argparse.ArgumentParser(description='Parse and compare python dependencies')
    ap.add_argument('command', choices=['report'])
    ap.add_argument('args', nargs=argparse.REMAINDER)
    args = ap.parse_args()

    return command_line_report(args.args)

if __name__ == '__main__':
    main()
