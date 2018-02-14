#!/usr/bin/env python
from setuptools import setup
import pypandoc
from pipsqueak import __version__


long_description = pypandoc.convert('README.md', 'rst')

setup(name='pipsqueak',
      version=__version__,
      description='Parse pip requirements files',
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
