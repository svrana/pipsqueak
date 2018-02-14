## pipsqueak ![Build Status][1] ![codecov][2]

Check installed dependencies against a pip requirements file, reporting
differences.

You can also use pipsqueak to parse a pip requirements file or parse the
output of pip freeze.

### How does it work?

pipsqueak runs 'pip freeze' and compares it against the requirements file that
you specify. The result is a dictionary that tells you which packages were
added, removed, upgraded or downgraded.

[1]: https://api.travis-ci.org/svrana/pipsqueak.svg?branch=master
[2]: https://codecov.io/gh/svrana/pipsqueak/branch/master/graph/badge.svg
