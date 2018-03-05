"""Handles all VCS (version control) support"""
import errno
import logging
import os

from six.moves.urllib import parse as urllib_parse

from pipsqueak.exceptions import BadCommand
from pipsqueak.pip.util import call_subprocess, display_path


__all__ = ['vcs', 'get_src_requirement']


logger = logging.getLogger(__name__)


class RevOptions(object):

    """
    Encapsulates a VCS-specific revision to install, along with any VCS
    install options.

    Instances of this class should be treated as if immutable.
    """

    def __init__(self, _vcs, rev=None, extra_args=None):
        """
        Args:
          vcs: a VersionControl object.
          rev: the name of the revision to install.
          extra_args: a list of extra options.
        """
        if extra_args is None:
            extra_args = []

        self.extra_args = extra_args
        self.rev = rev
        self.vcs = _vcs

    def __repr__(self):
        return '<RevOptions {}: rev={!r}>'.format(self.vcs.name, self.rev)

    @property
    def arg_rev(self):
        if self.rev is None:
            return self.vcs.default_arg_rev

        return self.rev

    def to_args(self):
        """
        Return the VCS-specific command arguments.
        """
        args = []
        rev = self.arg_rev
        if rev is not None:
            args += self.vcs.get_base_rev_args(rev)
        args += self.extra_args

        return args

    def to_display(self):
        if not self.rev:
            return ''

        return ' (to revision {})'.format(self.rev)

    def make_new(self, rev):
        """
        Make a copy of the current instance, but with a new rev.

        Args:
          rev: the name of the revision for the new object.
        """
        return self.vcs.make_rev_options(rev, extra_args=self.extra_args)


class VcsSupport(object):
    _registry = {}  # type: Dict[str, Command]
    schemes = ['ssh', 'git', 'hg', 'bzr', 'sftp', 'svn']

    def __init__(self):
        # Register more schemes with urlparse for various version control
        # systems
        urllib_parse.uses_netloc.extend(self.schemes)
        # Python >= 2.7.4, 3.3 doesn't have uses_fragment
        if getattr(urllib_parse, 'uses_fragment', None):
            urllib_parse.uses_fragment.extend(self.schemes)
        super(VcsSupport, self).__init__()

    def __iter__(self):
        return self._registry.__iter__()

    @property
    def backends(self):
        return list(self._registry.values())

    def backend_instances(self):
        return [cls() for cls in self._registry.values()]

    @property
    def dirnames(self):
        return [backend.dirname for backend in self.backends]

    @property
    def all_schemes(self):
        schemes = []
        for backend in self.backends:
            schemes.extend(backend.schemes)
        return schemes

    def register(self, cls):
        if not hasattr(cls, 'name'):
            logger.warning('Cannot register VCS %s', cls.__name__)
            return
        if cls.name not in self._registry:
            self._registry[cls.name] = cls
            logger.debug('Registered VCS backend: %s', cls.name)

    def unregister(self, cls=None, name=None):
        if name in self._registry:
            del self._registry[name]
        elif cls in self._registry.values():
            del self._registry[cls.name]
        else:
            logger.warning('Cannot unregister because no class or name given')

    def get_backend_name(self, location):
        """
        Return the name of the version control backend if found at given
        location, e.g. vcs.get_backend_name('/path/to/vcs/checkout')
        """
        for vc_type in self._registry.values():
            if vc_type.controls_location(location):
                logger.debug('Determine that %s uses VCS: %s',
                             location, vc_type.name)
                return vc_type.name
        return None

    def get_backend(self, name):
        name = name.lower()
        if name in self._registry:
            return self._registry[name]

    def get_backend_from_location(self, location):
        vc_type = self.get_backend_name(location)
        if vc_type:
            return self.get_backend(vc_type)
        return None


vcs = VcsSupport()


class VersionControl(object):
    name = ''
    dirname = ''
    # List of supported schemes for this Version Control
    schemes = ()  # type: Tuple[str, ...]
    # Iterable of environment variable names to pass to call_subprocess().
    unset_environ = ()  # type: Tuple[str, ...]
    default_arg_rev = None  # type: Optional[str]

    def __init__(self, url=None, *args, **kwargs):
        self.url = url
        super(VersionControl, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_base_rev_args(self, rev):
        """
        Return the base revision arguments for a vcs command.

        Args:
          rev: the name of a revision to install.  Cannot be None.
        """
        raise NotImplementedError

    def make_rev_options(self, rev=None, extra_args=None):
        """
        Return a RevOptions object.

        Args:
          rev: the name of a revision to install.
          extra_args: a list of extra options.
        """
        return RevOptions(self, rev, extra_args=extra_args)

    def _is_local_repository(self, repo):
        """
           posix absolute paths start with os.path.sep,
           win32 ones start with drive (like c:\\folder)
        """
        drive, tail = os.path.splitdrive(repo)
        return repo.startswith(os.path.sep) or drive

    # See issue #1083 for why this method was introduced:
    # https://github.com/pypa/pip/issues/1083
    def translate_egg_surname(self, surname):
        # For example, Django has branches of the form "stable/1.7.x".
        return surname.replace('/', '_')

    def get_url_rev(self):
        """
        Returns the correct repository URL and revision by parsing the given
        repository URL
        """
        error_message = (
            "Sorry, '%s' is a malformed VCS url. "
            "The format is <vcs>+<protocol>://<url>, "
            "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp"
        )
        assert '+' in self.url, error_message % self.url
        url = self.url.split('+', 1)[1]
        scheme, netloc, path, query, _ = urllib_parse.urlsplit(url)
        rev = None
        if '@' in path:
            path, rev = path.rsplit('@', 1)
        url = urllib_parse.urlunsplit((scheme, netloc, path, query, ''))
        return url, rev

    def get_info(self, location):
        """
        Returns (url, revision), where both are strings
        """
        assert not location.rstrip('/').endswith(self.dirname), \
            'Bad directory: %s' % location
        return self.get_url(location), self.get_revision(location)

    def normalize_url(self, url):
        """
        Normalize a URL for comparison by unquoting it and removing any
        trailing slash.
        """
        return urllib_parse.unquote(url).rstrip('/')

    def compare_urls(self, url1, url2):
        """
        Compare two repo URLs for identity, ignoring incidental differences.
        """
        return self.normalize_url(url1) == self.normalize_url(url2)

    def is_commit_id_equal(self, dest, name):
        """
        Return whether the id of the current commit equals the given name.

        Args:
          dest: the repository directory.
          name: a string name.
        """
        raise NotImplementedError

    def get_src_requirement(self, dist, location):
        """
        Return a string representing the requirement needed to
        redownload the files currently present in location, something
        like:
          {repository_url}@{revision}#egg={project_name}-{version_identifier}
        """
        raise NotImplementedError

    def get_url(self, location):
        """
        Return the url used at location
        Used in get_info or is_most_recent
        """
        raise NotImplementedError

    def get_revision(self, location):
        """
        Return the current commit id of the files at the given location.
        """
        raise NotImplementedError

    def get_latest_revision(self, url, rev):
        """
        Return the latest commit id specified by revision name (branch or tag)
        from the repo located at url.
        """
        raise NotImplementedError

    @classmethod
    def controls_location(cls, location):
        """
        Check if a location is controlled by the vcs.
        It is meant to be overridden to implement smarter detection
        mechanisms for specific vcs.
        """
        logger.debug('Checking in %s for %s (%s)...',
                     location, cls.dirname, cls.name)
        path = os.path.join(location, cls.dirname)
        return os.path.exists(path)

    def run_command(self, cmd, cwd=None,
                    on_returncode='raise',
                    command_desc=None,
                    extra_environ=None, spinner=None):
        """
        Run a VCS subcommand
        This is simply a wrapper around call_subprocess that adds the VCS
        command name, and checks that the VCS is available
        """
        cmd = [self.name] + cmd
        try:
            return call_subprocess(cmd, cwd,
                                   on_returncode,
                                   command_desc, extra_environ,
                                   unset_environ=self.unset_environ,
                                   spinner=spinner)
        except OSError as e:
            # errno.ENOENT = no such file or directory
            # In other words, the VCS executable isn't available
            if e.errno == errno.ENOENT:
                raise BadCommand(
                    'Cannot find command %r - do you have '
                    '%r installed and in your '
                    'PATH?' % (self.name, self.name))
            else:
                raise  # re-raise exception if a different error occurred

    def is_most_recent(self, dest, url, rev_options):
        """
        Return commit id ahead of the current location of dest if dest is
        behind upstream according to its rev_options. If rev_options does not
        contain a commit id, we must fetch the most recent commit ids from the
        upstream repo. To avoid going to the network, always specify a commit
        id instead of a branch. This has the benefit of producing reproducable
        builds.

        Modified from check_destination in pip.

        Args:
          rev_options: a RevOptions object.
        """
        existing_url = self.get_url(dest)
        upstream_rev = 'unknown'

        if self.compare_urls(existing_url, url):
            logger.debug(
                '%s in %s exists, and has correct URL (%s)',
                self.repo_name.title(),
                display_path(dest),
                url,
            )
            if self.is_commit_id_equal(dest, rev_options.rev):
                return True, ""

            current_rev = self.get_revision(dest)
            upstream_rev = self.get_latest_revision(url, rev_options.rev)
            if current_rev == upstream_rev:
                return True, ""

        return False, upstream_rev


def get_src_requirement(dist, location):
    version_control = vcs.get_backend_from_location(location)
    if version_control:
        try:
            return version_control().get_src_requirement(dist,
                                                         location)
        except Exception:
            logger.warning(
                'cannot determine version of editable source in %s '
                '(%s command not found in path)',
                location,
                version_control.name,
            )
            return dist.as_requirement()
    logger.warning(
        'cannot determine version of editable source in %s (is not SVN '
        'checkout, Git clone, Mercurial clone or Bazaar branch)',
        location,
    )
    return dist.as_requirement()


import pipsqueak.pip.vcs.git
import pipsqueak.pip.vcs.bazaar
import pipsqueak.pip.vcs.mercurial
import pipsqueak.pip.vcs.subversion
