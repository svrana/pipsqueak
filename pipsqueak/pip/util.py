from __future__ import absolute_import

import os
import posixpath
import sys
import subprocess
import logging

from six.moves.urllib import parse as urllib_parse
from six.moves.urllib import request as urllib_request
from six.moves.urllib.parse import unquote as urllib_unquote

from pipsqueak.pip.compat import console_to_str, expanduser

logger = logging.getLogger(__file__)


BZ2_EXTENSIONS = ('.tar.bz2', '.tbz')
XZ_EXTENSIONS = ('.tar.xz', '.txz', '.tlz', '.tar.lz', '.tar.lzma')
ZIP_EXTENSIONS = ('.zip', '.whl')
TAR_EXTENSIONS = ('.tar.gz', '.tgz', '.tar')
ARCHIVE_EXTENSIONS = (
    ZIP_EXTENSIONS + BZ2_EXTENSIONS + TAR_EXTENSIONS + XZ_EXTENSIONS
)

def display_path(path):
    """Gives the display value for a given path, making it relative to cwd
    if possible."""
    path = os.path.normcase(os.path.abspath(path))
    if sys.version_info[0] == 2:
        path = path.decode(sys.getfilesystemencoding(), 'replace')
        path = path.encode(sys.getdefaultencoding(), 'replace')
    if path.startswith(os.getcwd() + os.path.sep):
        path = '.' + path[len(os.getcwd()):]
    return path

def is_installable_dir(path):
    """Return True if `path` is a directory containing a setup.py file."""
    if not os.path.isdir(path):
        return False
    setup_py = os.path.join(path, 'setup.py')
    if os.path.isfile(setup_py):
        return True
    return False

def splitext(path):
    """Like os.path.splitext, but take off .tar too"""
    base, ext = posixpath.splitext(path)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext

def is_url(name):
    """Returns true if the name looks like a URL"""
    if ':' not in name:
        return False
    from pipsqueak.pip.vcs import vcs
    scheme = name.split(':', 1)[0].lower()
    return scheme in ['http', 'https', 'file', 'ftp'] + vcs.all_schemes

def url_to_path(url):
    """
    Convert a file: URL to a path.
    """
    assert url.startswith('file:'), (
        "You can only turn file: urls into filenames (not %r)" % url)

    _, netloc, path, _, _ = urllib_parse.urlsplit(url)

    # if we have a UNC path, prepend UNC share notation
    if netloc:
        netloc = '\\\\' + netloc

    path = urllib_request.url2pathname(netloc + path)
    return path

def path_to_url(path):
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
    url = urllib_parse.urljoin('file:', urllib_request.pathname2url(path))
    return url

def is_archive_file(name):
    """Return True if `name` is a considered as an archive file."""
    ext = splitext(name)[1].lower()
    if ext in ARCHIVE_EXTENSIONS:
        return True
    return False

def get_used_vcs_backend(link):
    from pipsqueak.pip.vcs import vcs

    for backend in vcs.backends:
        if link.scheme in backend.schemes:
            vcs_backend = backend(link.url)
            return vcs_backend

def call_subprocess(cmd, cwd=None,
                    on_returncode='raise',
                    command_desc=None,
                    extra_environ=None, unset_environ=None, spinner=None):
    """
    Args:
      unset_environ: an iterable of environment variable names to unset
        prior to calling subprocess.Popen().
    """
    if unset_environ is None:
        unset_environ = []
    # - We connect the child stdout to a pipe, which we read.
    # - By default, we hide the output but show a spinner -- unless the
    #   subprocess exits with an error, in which case we show the output.
    # - If the --verbose option was passed (= loglevel is DEBUG), then we show
    #   the output unconditionally. (But in this case we don't want to show
    #   the output a second time if it turns out that there was an error.)
    #
    # stderr is always merged with stdout
    stdout = subprocess.PIPE
    if command_desc is None:
        cmd_parts = []
        for part in cmd:
            if ' ' in part or '\n' in part or '"' in part or "'" in part:
                part = '"%s"' % part.replace('"', '\\"')
            cmd_parts.append(part)
        command_desc = ' '.join(cmd_parts)
    logger.debug("Running command %s", command_desc)
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)
    for name in unset_environ:
        env.pop(name, None)
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            stdout=stdout, cwd=cwd, env=env,
        )
        proc.stdin.close()
    except Exception as exc:
        logger.critical(
            "Error %s while executing command %s", exc, command_desc,
        )
        raise
    all_output = []
    if stdout is not None:
        while True:
            line = console_to_str(proc.stdout.readline())
            if not line:
                break
            line = line.rstrip()
            all_output.append(line + '\n')
            # Show the line immediately
            logger.debug(line)
    try:
        proc.wait()
    finally:
        if proc.stdout:
            proc.stdout.close()
    if spinner is not None:
        if proc.returncode:
            spinner.finish("error")
        else:
            spinner.finish("done")
    if proc.returncode:
        if on_returncode == 'raise':
            raise Exception(
                'Command "%s" failed with error code %s in %s'
                % (command_desc, proc.returncode, cwd))
        elif on_returncode == 'warn':
            logger.warning(
                'Command "%s" had error code %s in %s',
                command_desc, proc.returncode, cwd,
            )
        elif on_returncode == 'ignore':
            pass
        else:
            raise ValueError('Invalid value: on_returncode=%s' %
                             repr(on_returncode))
    return ''.join(all_output)

def normalize_path(path, resolve_symlinks=True):
    """
    Convert a path to its canonical, case-normalized, absolute version.

    """
    path = expanduser(path)
    if resolve_symlinks:
        path = os.path.realpath(path)
    else:
        path = os.path.abspath(path)
    return os.path.normcase(path)

def dist_is_editable(dist):
    """ Is distribution an editable install? """
    for path_item in sys.path:
        egg_link = os.path.join(path_item, dist.project_name + '.egg-link')
        if os.path.isfile(egg_link):
            return True
    return False

def is_file_url(link):
    return link.url.lower().startswith('file:')
