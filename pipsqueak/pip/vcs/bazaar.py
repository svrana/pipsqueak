from __future__ import absolute_import

import logging

from six.moves.urllib import parse as urllib_parse

from pipsqueak.pip.util import path_to_url
from pipsqueak.pip.vcs import VersionControl, vcs

logger = logging.getLogger(__name__)


class Bazaar(VersionControl):
    name = 'bzr'
    dirname = '.bzr'
    repo_name = 'branch'
    schemes = (
        'bzr', 'bzr+http', 'bzr+https', 'bzr+ssh', 'bzr+sftp', 'bzr+ftp',
        'bzr+lp',
    )

    def __init__(self, url=None, *args, **kwargs):
        super(Bazaar, self).__init__(url, *args, **kwargs)
        # This is only needed for python <2.7.5
        # Register lp but do not expose as a scheme to support bzr+lp.
        if getattr(urllib_parse, 'uses_fragment', None):
            urllib_parse.uses_fragment.extend(['lp'])

    def get_base_rev_args(self, rev):
        return ['-r', rev]

    def get_url_rev(self):
        # hotfix the URL scheme after removing bzr+ from bzr+ssh:// readd it
        url, rev = super(Bazaar, self).get_url_rev()
        if url.startswith('ssh://'):
            url = 'bzr+' + url
        return url, rev

    def get_url(self, location):
        urls = self.run_command(['info'], cwd=location)
        for line in urls.splitlines():
            line = line.strip()
            for x in ('checkout of branch: ',
                      'parent branch: '):
                if line.startswith(x):
                    repo = line.split(x)[1]
                    if self._is_local_repository(repo):
                        return path_to_url(repo)
                    return repo
        return None

    def get_revision(self, location):
        revision = self.run_command(
            ['revno'], cwd=location,
        )
        return revision.splitlines()[-1]

    def get_src_requirement(self, dist, location):
        repo = self.get_url(location)
        if not repo:
            return None
        if not repo.lower().startswith('bzr:'):
            repo = 'bzr+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        current_rev = self.get_revision(location)
        return '%s@%s#egg=%s' % (repo, current_rev, egg_project_name)

    def is_commit_id_equal(self, dest, name):
        """Always assume the versions don't match"""
        return False


vcs.register(Bazaar)
