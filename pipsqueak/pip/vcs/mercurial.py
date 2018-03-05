from __future__ import absolute_import

from pipsqueak.pip.util import path_to_url
from pipsqueak.pip.vcs import VersionControl, vcs


class Mercurial(VersionControl):
    name = 'hg'
    dirname = '.hg'
    repo_name = 'clone'
    schemes = ('hg', 'hg+http', 'hg+https', 'hg+ssh', 'hg+static-http')

    def get_base_rev_args(self, rev):
        return [rev]

    def get_url(self, location):
        url = self.run_command(
            ['showconfig', 'paths.default'], cwd=location).strip()
        if self._is_local_repository(url):
            url = path_to_url(url)
        return url.strip()

    def get_revision(self, location):
        current_revision = self.run_command(
            ['parents', '--template={rev}'],
            cwd=location).strip()
        return current_revision

    def get_revision_hash(self, location):
        current_rev_hash = self.run_command(
            ['parents', '--template={node}'],
            cwd=location).strip()
        return current_rev_hash

    def get_src_requirement(self, dist, location):
        repo = self.get_url(location)
        if not repo.lower().startswith('hg:'):
            repo = 'hg+' + repo
        egg_project_name = dist.egg_name().split('-', 1)[0]
        if not repo:
            return None
        current_rev_hash = self.get_revision_hash(location)
        return '%s@%s#egg=%s' % (repo, current_rev_hash, egg_project_name)

    def is_commit_id_equal(self, dest, name):
        """Always assume the versions don't match"""
        return False


vcs.register(Mercurial)
