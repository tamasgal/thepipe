# -*- coding: utf-8 -*-
# Filename: __version__.py
"""
Pep 386 compliant version info.

    (major, minor, micro, alpha/beta/rc/final, #)
    (1, 1, 2, 'alpha', 0) => "1.1.2.dev"
    (1, 2, 0, 'beta', 2) => "1.2b2"

"""
from __future__ import absolute_import, print_function, division

from os.path import dirname, realpath, join

from setuptools_scm import get_version

version = 'unknown version'

try:
    version = get_version(root='..', relative_to=__file__)
except LookupError:
    with open(join(realpath(dirname(__file__)), "version.txt"), 'r') as fobj:
        version = fobj.read()
