from __future__ import absolute_import

import os
import posixpath
import sys

from six.moves.urllib import parse as urllib_parse
from six.moves.urllib import request as urllib_request
from six.moves.urllib.parse import unquote as urllib_unquote


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

def unpack_vcs_link(link, location):
    vcs_backend = get_used_vcs_backend(link)
    vcs_backend.unpack(location)

def get_used_vcs_backend(link):
    from pipsqueak.pip.vcs import vcs

    for backend in vcs.backends:
        if link.scheme in backend.schemes:
            vcs_backend = backend(link.url)
            return vcs_backend
