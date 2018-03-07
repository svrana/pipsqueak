#!/usr/bin/env python

from setuptools import setup, find_packages
from pipsqueak import __version__

try:
    import pypandoc  # also requires the pandoc package
    long_description = pypandoc.convert('README.md', 'rst')
except Exception:
    f = open('README.md')
    long_description = f.read()
    f.close()


def get_requirements(env):
    with open('requirements-{}.txt'.format(env)) as fp:
        return [x.strip() for x in fp.read().split('\n')
                if not x.startswith('#')]


install_requires = get_requirements('base')
tests_require = get_requirements('test')
dev_requires = get_requirements('dev')


setup(
    name='pipsqueak',
    version=__version__,
    description='Parse and compare pip requirements',
    long_description=long_description,
    url='http://github.com/svrana/pipsqueak',
    author='Shaw Vrana',
    author_email='shaw@vranix.com',
    license='MIT',
    packages=find_packages('.', exclude=["*.test", "*.test.*",
                                         "test.*", "test"]),
    include_package_data=True,
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    install_requires=install_requires,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'pipsqueak = pipsqueak.main:main',
        ],
    },
    extras_require={
        'tests': tests_require,
        'dev': dev_requires,
    },
)
