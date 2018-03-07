import logging
import os
import re
import traceback
import pkg_resources
import six

from packaging import specifiers
from packaging.markers import Marker
from packaging.requirements import InvalidRequirement, Requirement

from pipsqueak.pip.util import (
    display_path,
    is_installable_dir,
    url_to_path,
    is_archive_file,
    is_url,
    path_to_url,
)
from pipsqueak.exceptions import (
    ConfigurationError,
    RequirementParseError,
)
from pipsqueak.pip.link import Link
from pipsqueak.pip.vcs import vcs
from pipsqueak.pip.wheel import Wheel


logger = logging.getLogger(__name__)
operators = specifiers.Specifier._operators.keys()


def _strip_extras(path):
    m = re.match(r'^(.+)(\[[^\]]+\])$', path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


class InstallRequirement(object):
    """
    Represents something that may be installed later on, may have information
    about where to fetch the relavant requirement and also contains logic for
    installing the said requirement.
    """

    def __init__(self, req, comes_from, source_dir=None, editable=False,
                 link=None, update=True, pycompile=True, markers=None,
                 isolated=False, options=None, wheel_cache=None,
                 constraint=False, extras=()):
        assert req is None or isinstance(req, Requirement), req
        self.req = req
        self.comes_from = comes_from
        self.constraint = constraint
        if source_dir is not None:
            self.source_dir = os.path.normpath(os.path.abspath(source_dir))
        else:
            self.source_dir = None
        self.editable = editable

        self._wheel_cache = wheel_cache
        if link is not None:
            self.link = self.original_link = link
        else:
            self.link = self.original_link = req and req.url and Link(req.url)

        if extras:
            self.extras = extras
        elif req:
            self.extras = {
                pkg_resources.safe_extra(extra) for extra in req.extras
            }
        else:
            self.extras = set()
        if markers is not None:
            self.markers = markers
        else:
            self.markers = req and req.marker
        self._egg_info_path = None
        # This holds the pkg_resources.Distribution object if this requirement
        # is already available:
        self.satisfied_by = None
        # True if the editable should be updated:
        self.update = update
        # Set to True after successful installation
        self.install_succeeded = None
        # UninstallPathSet of uninstalled distribution (for possible rollback)
        self.uninstalled_pathset = None
        self.use_user_site = False
        self.target_dir = None
        self.options = options if options else {}
        self.pycompile = pycompile
        # Set to True after successful preparation of this requirement
        self.prepared = False

        self.isolated = isolated

    @classmethod
    def from_editable(cls, editable_req, comes_from=None, isolated=False,
                      options=None, wheel_cache=None, constraint=False):
        name, url, extras_override = parse_editable(editable_req)
        if url.startswith('file:'):
            source_dir = url_to_path(url)
        else:
            source_dir = None

        if name is not None:
            try:
                req = Requirement(name)
            except InvalidRequirement:
                raise RequirementParseError("Invalid requirement: '%s'" % name)
        else:
            req = None
        return cls(
            req, comes_from, source_dir=source_dir,
            editable=True,
            link=Link(url),
            constraint=constraint,
            isolated=isolated,
            options=options if options else {},
            wheel_cache=wheel_cache,
            extras=extras_override or (),
        )

    @classmethod
    def from_req(cls, req, comes_from=None, isolated=False, wheel_cache=None):
        try:
            req = Requirement(req)
        except InvalidRequirement:
            raise RequirementParseError("Invalid requirement: '%s'" % req)
        if req.url:
            raise ConfigurationError(
                "Direct url requirement (like %s) are not allowed for "
                "dependencies" % req
            )
        return cls(req, comes_from, isolated=isolated, wheel_cache=wheel_cache)

    @classmethod
    def from_line(
            cls, name, comes_from=None, isolated=False, options=None,
            wheel_cache=None, constraint=False):
        """Creates an InstallRequirement from a name, which might be a
        requirement, directory containing 'setup.py', filename, or URL.
        """
        if is_url(name):
            marker_sep = '; '
        else:
            marker_sep = ';'
        if marker_sep in name:
            name, markers = name.split(marker_sep, 1)
            markers = markers.strip()
            if not markers:
                markers = None
            else:
                markers = Marker(markers)
        else:
            markers = None

        name = name.strip()
        req = None
        path = os.path.normpath(os.path.abspath(name))
        link = None
        extras = None

        if is_url(name):
            link = Link(name)
        else:
            p, extras = _strip_extras(path)
            looks_like_dir = os.path.isdir(p) and (
                os.path.sep in name or
                (os.path.altsep is not None and os.path.altsep in name) or
                name.startswith('.')
            )
            if looks_like_dir:
                if not is_installable_dir(p):
                    raise RequirementParseError(
                        "Directory %r is not installable. File 'setup.py' "
                        "not found." % name
                    )
                link = Link(path_to_url(p))
            elif is_archive_file(p):
                if not os.path.isfile(p):
                    logger.warning(
                        'Requirement %r looks like a filename, but the '
                        'file does not exist',
                        name
                    )
                link = Link(path_to_url(p))

        # it's a local file, dir, or url
        if link:
            # Handle relative file URLs
            if link.scheme == 'file' and re.search(r'\.\./', link.url):
                link = Link(
                    path_to_url(os.path.normpath(os.path.abspath(link.path))))
            # wheel file
            if link.is_wheel:
                wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
                req = "%s==%s" % (wheel.name, wheel.version)
            else:
                # set the req to the egg fragment.  when it's not there, this
                # will become an 'unnamed' requirement
                req = link.egg_fragment

        # a requirement specifier
        else:
            req = name

        if extras:
            extras = Requirement("placeholder" + extras.lower()).extras
        else:
            extras = ()
        if req is not None:
            try:
                req = Requirement(req)
            except InvalidRequirement:
                if os.path.sep in req:
                    add_msg = "It looks like a path."
                elif '=' in req and not any(op in req for op in operators):
                    add_msg = "= is not a valid operator. Did you mean == ?"
                else:
                    add_msg = traceback.format_exc()
                raise RequirementParseError(
                    "Invalid requirement: '%s'\n%s" % (req, add_msg))
        return cls(
            req, comes_from, link=link, markers=markers,
            isolated=isolated,
            options=options if options else {},
            wheel_cache=wheel_cache,
            constraint=constraint,
            extras=extras,
        )

    def __str__(self):
        if self.req:
            s = str(self.req)
            if self.link:
                s += ' from %s' % self.link.url
        else:
            s = self.link.url if self.link else None
        if self.satisfied_by is not None:
            s += ' in %s' % display_path(self.satisfied_by.location)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += ' (from %s)' % comes_from
        return s

    def __repr__(self):
        return '<%s object: %s editable=%r>' % (
            self.__class__.__name__, str(self), self.editable)

    @property
    def specifier(self):
        return self.req.specifier

    @property
    def is_pinned(self):
        """Return whether I am pinned to an exact version.

        For example, some-package==1.2 is pinned; some-package>1.2 is not.
        """
        specs = self.specifier
        return (len(specs) == 1 and
                next(iter(specs)).operator in {'==', '==='})

    def from_path(self):
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += '->' + comes_from
        return s

    @property
    def name(self):
        if self.req is None:
            return None
        return pkg_resources.safe_name(self.req.name)

    @property
    def setup_py_dir(self):
        return os.path.join(
            self.source_dir,
            self.link and self.link.subdirectory_fragment or '')

    def match_markers(self, extras_requested=None):
        if not extras_requested:
            # Provide an extra to safely evaluate the markers
            # without matching any extra
            extras_requested = ('',)
        if self.markers is not None:
            return any(
                self.markers.evaluate({'extra': extra})
                for extra in extras_requested)
        else:
            return True

    @property
    def is_wheel(self):
        return self.link and self.link.is_wheel

    @property
    def has_hash_options(self):
        """Return whether any known-good hashes are specified as options.

        These activate --require-hashes mode; hashes specified as part of a
        URL do not.

        """
        return bool(self.options.get('hashes', {}))


def _strip_postfix(req):
    """ Strip req postfix ( -dev, 0.2, etc ) """
    match = re.search(r'^(.*?)(?:-dev|-\d.*)$', req)
    if match:
        req = match.group(1)
    return req


def parse_editable(editable_req):
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """
    url = editable_req

    # If a file path is specified with extras, strip off the extras.
    url_no_extras, extras = _strip_extras(url)

    if os.path.isdir(url_no_extras):
        if not os.path.exists(os.path.join(url_no_extras, 'setup.py')):
            raise RequirementParseError(
                "Directory %r is not installable. File 'setup.py' not found." %
                url_no_extras
            )
        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith('file:'):
        package_name = Link(url_no_extras).egg_fragment
        if extras:
            return (
                package_name,
                url_no_extras,
                Requirement("placeholder" + extras.lower()).extras,
            )
        else:
            return package_name, url_no_extras, None

    for version_control in vcs.backend_instances():
        if url.lower().startswith('%s:' % version_control):
            url = '%s+%s' % (version_control, url)
            break

    if '+' not in url:
        raise InvalidRequirement(
            '%s should either be a path to a local project or a VCS url '
            'beginning with svn+, git+, hg+, or bzr+' %
            editable_req
        )

    vc_type = url.split('+', 1)[0].lower()

    if not vcs.get_backend(vc_type):
        error_message = 'For --editable=%s only ' % editable_req + \
            ', '.join([backend.name + '+URL' for backend in vcs.backends]) + \
            ' is currently supported'
        raise InvalidRequirement(error_message)

    package_name = Link(url).egg_fragment
    if not package_name:
        raise Exception(
            "Could not detect requirement name for '%s', please specify one "
            "with #egg=your_package_name" % editable_req
        )
    return _strip_postfix(package_name), url, None
