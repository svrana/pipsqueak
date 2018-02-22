from __future__ import absolute_import

import os

from six.moves.urllib import parse as urllib_parse
from six.moves.urllib import request as urllib_request
from six.moves.urllib.parse import unquote as urllib_unquote


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
    from pipsqueak.pip.common import splitext, ARCHIVE_EXTENSIONS
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

def is_vcs_url(link):
    return bool(get_used_vcs_backend(link))

def is_file_url(link):
    return link.url.lower().startswith('file:')

def is_dir_url(link):
    """Return whether a file:// Link points to a directory.

    ``link`` must not have any other scheme but file://. Call is_file_url()
    first.

    """
    link_path = url_to_path(link.url_without_fragment)
    return os.path.isdir(link_path)
