#!/usr/bin/env python
# Filename: setup.py
"""
thepipe setup script.

"""

from setuptools import setup

try:
    import builtins
except ImportError:
    import __builtin__ as builtins
# so we can detect in __init__.py that it's called from setup.py
builtins.__THEPIPE_SETUP__ = True

with open('requirements/install.txt') as fobj:
    requirements = [l.strip() for l in fobj.readlines()]

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='thepipe',
    url='http://github.com/tamasgal/thepipe',
    description='A lightweight, general purpose pipeline framework.',
    long_description=long_description,
    author='Tamas Gal',
    author_email='tgal@km3net.de',
    packages=['thepipe'],
    include_package_data=True,
    platforms='any',
    setup_requires=['setuptools_scm'],
    use_scm_version={
        'write_to': 'thepipe/version.txt',
        'tag_regex': r'^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$',
    },
    install_requires=requirements,
    python_requires='>=3.5',
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
    ],
)
