import os.path
import re
from subprocess import Popen, PIPE


PYPI_MATCH= r"([\w|\-|\.]+)\s*(\W\W)\s*([\w|\W]+)"

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
            raise Exception("Could not find project name of for '%s'", req)
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

    start_loc = req.index("://") + len("://")
    return req[start_loc:end_loc]

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

def parse_requirements_file(requirements):
    requirements = os.path.abspath(requirements)
    if not os.path.exists(requirements):
        raise Exception("Could not locate requirements file %s", requirements)

    with open(requirements) as reqs:
        modules = parse_requirements(reqs)
        for _, details in modules.iteritems():
            # ones that are loaded from a sub requirment will have their
            # source specified already
            if details['source'] is None:
                details['source'] = requirements
        return modules

def _get_pip_freeze_output():
    process = Popen(["pip", "freeze", "."], stdout=PIPE)
    output, _ = process.communicate()
    reqs = [line for line in output.split('\n') if line]
    return reqs

def parse_installed():
    reqs = _get_pip_freeze_output()
    required = parse_requirements(reqs)

def report(requirements):
    required = parse_requirements_file(requirements)
    installed = parse_installed()
