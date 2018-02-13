#!/usr/bin/env python
import os
from setuptools import setup
from pipsqueak import __version__


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    long_description = readme.read()

setup(name='pipsqueak',
      version=__version__,
      description='Report on differences between installed pip dependencies and their requirements',
      long_description=long_description,
      url='http://github.com/svrana/pipsqueak',
      author='Shaw Vrana',
      author_email='shaw@vranix.com',
      license='MIT',
      packages=['pipsqueak'],
      classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',

      ],
      install_requires=[
      ],
      zip_safe=False,
      )
