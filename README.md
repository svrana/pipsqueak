## Pipsqueak

Check installed dependencies dependencies against requirement, reporting
differences. You can also use pipsqueak to parse your pip requirements file
or the output of pip freeze.

### How does it work?

pipcheck runs 'pip freeze' and compares it against the requirements file that
you specify. The result is a dictionary that tells you which packages were
added, removed, upgraded or downgraded.
