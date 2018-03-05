import os
import re
import logging

from pipsqueak.pip.vcs import vcs, get_src_requirement
from pipsqueak.pip.util import dist_is_editable

logger = logging.getLogger(__file__)

class FrozenRequirement(object):
    def __init__(self, name, req, editable, location, comments=()):
        self.name = name
        self.req = req
        self.editable = editable
        self.comments = comments
        self.location = location

    _rev_re = re.compile(r'-r(\d+)$')
    _date_re = re.compile(r'-(20\d\d\d\d\d\d)$')

    @classmethod
    def from_dist(cls, dist, dependency_links):
        location = os.path.normcase(os.path.abspath(dist.location))
        comments = []

        if dist_is_editable(dist) and vcs.get_backend_name(location):
            editable = True
            try:
                req = get_src_requirement(dist, location)
            except Exception as exc:
                logger.warning(
                    "Error when trying to get requirement for VCS system %s, "
                    "falling back to uneditable format", exc
                )
                req = None
            if req is None:
                logger.warning(
                    'Could not determine repository location of %s', location
                )
                comments.append(
                    '## !! Could not determine repository location'
                )
                req = dist.as_requirement()
                editable = False
        else:
            editable = False
            req = dist.as_requirement()
            specs = req.specs
            assert len(specs) == 1 and specs[0][0] in ["==", "==="], \
                'Expected 1 spec with == or ===; specs = %r; dist = %r' % \
                (specs, dist)
            version = specs[0][1]
            ver_match = cls._rev_re.search(version)
            date_match = cls._date_re.search(version)
            if ver_match or date_match:
                svn_backend = vcs.get_backend('svn')
                if svn_backend:
                    svn_location = svn_backend().get_location(
                        dist,
                        dependency_links,
                    )
                if not svn_location:
                    logger.warning(
                        'Warning: cannot find svn location for %s', req,
                    )
                    comments.append(
                        '## FIXME: could not find svn URL in dependency_links '
                        'for this package:'
                    )
                else:
                    logger.warn(
                        "SVN editable detection based on dependency links "
                        "will be dropped in the future.",
                    )
                    comments.append(
                        '# Installing as editable to satisfy requirement %s:' %
                        req
                    )
                    if ver_match:
                        rev = ver_match.group(1)
                    else:
                        rev = '{%s}' % date_match.group(1)
                    editable = True
                    req = '%s@%s#egg=%s' % (
                        svn_location,
                        rev,
                        cls.egg_name(dist)
                    )

        logger.info("found: %s", dist.project_name)
        return cls(dist.project_name, req, editable, location, comments)

    @staticmethod
    def egg_name(dist):
        name = dist.egg_name()
        match = re.search(r'-py\d\.\d$', name)
        if match:
            name = name[:match.start()]
        return name

    def __str__(self):
        req = self.req
        if self.editable:
            req = '-e %s' % req
        return '\n'.join(list(self.comments) + [str(req)]) + '\n'
