from functools import partial
import optparse
from optparse import Option

from pipsqueak.pip.index import PyPI
from pipsqueak.exceptions import RequirementsFileParseError


def constraints():
    return Option(
        '-c', '--constraint',
        dest='constraints',
        action='append',
        default=[],
        metavar='file',
        help='Constrain versions using the given constraints file. '
        'This option can be used multiple times.'
    )


def requirements():
    return Option(
        '-r', '--requirement',
        dest='requirements',
        action='append',
        default=[],
        metavar='file',
        help='Install from the given requirements file. '
        'This option can be used multiple times.'
    )


def editable():
    return Option(
        '-e', '--editable',
        dest='editables',
        action='append',
        default=[],
        metavar='path/url',
        help=('Install a project in editable mode (i.e. setuptools '
              '"develop mode") from a local project path or a VCS url.'),
    )


no_index = partial(
    Option,
    '--no-index',
    dest='no_index',
    action='store_true',
    default=False,
    help='Ignore package index (only looking at --find-links URLs instead).',
)


def find_links():
    return Option(
        '-f', '--find-links',
        dest='find_links',
        action='append',
        default=[],
        metavar='url',
        help="If a url or path to an html file, then parse for links to "
             "archives. If a local path or file:// url that's a directory, "
             "then look for archives in the directory listing.",
    )


def trusted_host():
    return Option(
        "--trusted-host",
        dest="trusted_hosts",
        action="append",
        metavar="HOSTNAME",
        default=[],
        help="Mark this host as trusted, even though it does not have valid "
             "or any HTTPS.",
    )


index_url = partial(
    Option,
    '-i', '--index-url', '--pypi-url',
    dest='index_url',
    metavar='URL',
    default=PyPI.simple_url,
    help="Base URL of Python Package Index (default %default). "
         "This should point to a repository compliant with PEP 503 "
         "(the simple repository API) or a local directory laid out "
         "in the same format.",
)


def extra_index_url():
    return Option(
        '--extra-index-url',
        dest='extra_index_urls',
        metavar='URL',
        action='append',
        default=[],
        help="Extra URLs of package indexes to use in addition to "
             "--index-url. Should follow the same rules as "
             "--index-url.",
    )


require_hashes = partial(
    Option,
    '--require-hashes',
    dest='require_hashes',
    action='store_true',
    default=False,
    help='Require a hash to check each requirement against, for '
         'repeatable installs. This option is implied when any package in a '
         'requirements file has a --hash option.',
)


SUPPORTED_OPTIONS = [
    constraints,
    editable,
    requirements,
    no_index,
    index_url,
    find_links,
    extra_index_url,
    trusted_host,
    require_hashes,
]


def break_args_options(line):
    """Break up the line into an args and options string.  We only want to shlex
    (and then optparse) the options, not the args.  args can contain markers
    which are corrupted by shlex.
    """
    tokens = line.split(' ')
    args = []
    options = tokens[:]
    for token in tokens:
        if token.startswith('-') or token.startswith('--'):
            break
        else:
            args.append(token)
            options.pop(0)
    return ' '.join(args), ' '.join(options)


def build_parser(line):
    """
    Return a parser for parsing requirement lines
    """
    parser = optparse.OptionParser(add_help_option=False)

    option_factories = SUPPORTED_OPTIONS
    for option_factory in option_factories:
        option = option_factory()
        parser.add_option(option)

    # By default optparse sys.exits on parsing errors. We want to wrap
    # that in our own exception.
    def parser_exit(_, msg):
        # add offending line
        msg = 'Invalid requirement: %s\n%s' % (line, msg)
        raise RequirementsFileParseError(msg)
    parser.exit = parser_exit
    parser.exit = parser_exit

    return parser
