# -*- coding: utf-8 -*-
# Filename: logger.py
"""
The logging facility.

"""
from hashlib import sha256
from inspect import getframeinfo, stack
import socket
import logging

from .tools import colored, supports_color

__author__ = "Tamas Gal"
__credits__ = []
__license__ = "MIT"
__email__ = "tgal@km3net.de"

LOGGERS = {}  # this holds all the registered loggers

DEPRECATION = 45
logging.addLevelName(DEPRECATION, "DEPRECATION")
ONCE = 46
logging.addLevelName(ONCE, "ONCE")


def deprecation(self, message, *args, **kws):
    """Show a deprecation warning."""
    self._log(DEPRECATION, message, args, **kws)


def once(self, message, *args, identifier=None, **kws):
    """Show a message only once, determined by position in source or identifer.

    This will not work in IPython or Jupyter notebooks if no identifier is
    specified, since then the determined position in source contains the
    execution number of the input (cell), which changes every time.
    Set a unique identifier, otherwise the message will be printed every
    time.
    """
    if identifier is None:
        caller = getframeinfo(stack()[1][0])
        identifier = "%s:%d" % (caller.filename, caller.lineno)
    if not hasattr(self, 'once_dict'):
        self.once_dict = {}
    if identifier in self.once_dict:
        return
    self.once_dict[identifier] = True
    self._log(ONCE, message, args, **kws)


logging.Logger.deprecation = deprecation
logging.Logger.once = once

if supports_color():
    logging.addLevelName(
        logging.INFO,
        "\033[1;32m%s\033[1;0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName(
        logging.DEBUG,
        "\033[1;34m%s\033[1;0m" % logging.getLevelName(logging.DEBUG))
    logging.addLevelName(
        logging.WARNING,
        "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    logging.addLevelName(
        logging.ERROR,
        "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName(
        logging.CRITICAL,
        "\033[1;101m%s\033[1;0m" % logging.getLevelName(logging.CRITICAL))
    logging.addLevelName(DEPRECATION, "\033[1;35m%s\033[1;0m" % 'DEPRECATION')
    logging.addLevelName(ONCE, "\033[1;36m%s\033[1;0m" % 'ONCE')


def get_logger(name):
    """Helper function to get a logger"""
    if name in LOGGERS:
        return LOGGERS[name]
    logger = logging.getLogger(name)
    logger.propagate = False

    if supports_color():
        pre1, suf1 = hash_coloured_escapes(name)
        pre2, suf2 = hash_coloured_escapes(name + 'salt')
    else:
        pre1, suf1, pre2, suf2 = ('', '', '', '')

    formatter = logging.Formatter('%(levelname)s {}+{}+{} '
                                  '%(name)s: %(message)s'.format(
                                      pre1, pre2, suf1))
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    LOGGERS[name] = logger

    logger.once_dict = {}

    return logger


def available_loggers():
    """Return a list of avialable logger names"""
    return list(logging.Logger.manager.loggerDict.keys())


def set_level(name, level):
    """Set the log level for given logger"""
    get_logger(name).setLevel(level)


def get_printer(name, color=None, ansi_code=None, force_color=False):
    """Return a function which prints a message with a coloured name prefix"""

    if force_color or supports_color():
        if color is None and ansi_code is None:
            cpre_1, csuf_1 = hash_coloured_escapes(name)
            cpre_2, csuf_2 = hash_coloured_escapes(name + 'salt')
            name = cpre_1 + '+' + cpre_2 + '+' + csuf_1 + ' ' + name
        else:
            name = colored(name, color=color, ansi_code=ansi_code)

    prefix = name + ': '

    def printer(text):
        print(prefix + str(text))

    return printer


def hash_coloured(text):
    """Return a ANSI coloured text based on its hash"""
    ansi_code = int(sha256(text.encode('utf-8')).hexdigest(), 16) % 230
    return colored(text, ansi_code=ansi_code)


def hash_coloured_escapes(text):
    """Return the ANSI hash colour prefix and suffix for a given text"""
    ansi_code = int(sha256(text.encode('utf-8')).hexdigest(), 16) % 230
    prefix, suffix = colored('SPLIT', ansi_code=ansi_code).split('SPLIT')
    return prefix, suffix
