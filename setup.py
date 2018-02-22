#!/usr/bin/env python
from setuptools import setup
from pipsqueak import __version__

try:
    import pypandoc # also requires the pandoc package
    long_description = pypandoc.convert('README.md', 'rst')
except Exception:
    f = open('README.md')
    long_description = f.read()
    f.close()

with open('dev-requirements.txt') as f:
    tests_require = f.read().split('\n')

setup(name='pipsqueak',
      version=__version__,
      description='Parse pip requirements files',
      long_description=long_description,
      url='http://github.com/svrana/pipsqueak',
      author='Shaw Vrana',
      author_email='shaw@vranix.com',
      license='MIT',
      packages=['pipsqueak', 'pipsqueak.pip', 'pipsqueak.pip.vcs'],
      classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      install_requires=[
          'six',
          'packaging',
          'ipaddress',
      ],
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'pipsqueak = pipsqueak.main:main',
          ],
      },
      tests_require=tests_require,
      extras_require={
            'testing': tests_require,
       },
)

