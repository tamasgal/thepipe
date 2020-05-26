# -*- coding: utf-8 -*-
# Filename: logger.py
"""
The logging facility.

"""
from datetime import datetime
from hashlib import sha256
from inspect import getframeinfo, stack
import logging

from .tools import colored, supports_color

__author__ = "Tamas Gal"
__credits__ = [
    "Sam Clements for all the colours! "
    "https://github.com/borntyping/python-colorlog"
]
__license__ = "MIT"
__email__ = "tgal@km3net.de"

DEFAULT_LOG_COLORS = {
    'DEBUG': 'thin_white',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
    'ONCE': 'cyan',
    'DEPRECATION': 'bold_blue'
}

LOGGERS = {}  # this holds all the registered loggers
DEPRECATION = 45
logging.addLevelName(DEPRECATION, "DEPRECATION")
ONCE = 46
logging.addLevelName(ONCE, "ONCE")
DATEFMT = '%Y-%m-%d %H:%M:%S'


def deprecation(self, message, *args, **kwargs):
    """Show a deprecation warning."""
    self._log(DEPRECATION, message, args, **kwargs)


logging.Logger.deprecation = deprecation


def once(self, message, *args, identifier=None, **kwargs):
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
    self._log(ONCE, message, args, **kwargs)


logging.Logger.once = once


def esc(*x):
    """Create escaped code from format code"""
    return '\033[' + ';'.join(x) + 'm'


# The following coloured log logic is from
# https://github.com/borntyping/python-colorlog
# I dropped some features and removed the Python 2.7 compatibility

ESCAPE_CODES = {'reset': esc('0'), 'bold': esc('01'), 'thin': esc('02')}

COLORS = ['black', 'red', 'green', 'yellow', 'blue', 'purple', 'cyan', 'white']

PREFIXES = [
    # Foreground without prefix
    ('3', ''),
    ('01;3', 'bold_'),
    ('02;3', 'thin_'),

    # Foreground with fg_ prefix
    ('3', 'fg_'),
    ('01;3', 'fg_bold_'),
    ('02;3', 'fg_thin_'),

    # Background with bg_ prefix - bold/light works differently
    ('4', 'bg_'),
    ('10', 'bg_bold_'),
]

for _prefix, _prefix_name in PREFIXES:
    for _code, _name in enumerate(COLORS):
        ESCAPE_CODES[_prefix_name + _name] = esc(_prefix + str(_code))


def parse_colors(sequence):
    """Return escape codes from a color sequence."""
    return ''.join(ESCAPE_CODES[n] for n in sequence.split(',') if n)


class ColoredRecord:
    """
    Wraps a LogRecord, adding named escape codes to the internal dict.
    The internal dict is used when formatting the message (by the PercentStyle,
    StrFormatStyle, and StringTemplateStyle classes).
    """

    def __init__(self, record):
        """Add attributes from the escape_codes dict and the record."""
        self.__dict__.update(ESCAPE_CODES)
        self.__dict__.update(record.__dict__)
        self.__record = record

    def __getattr__(self, name):
        return getattr(self.__record, name)


class ColouredFormatter(logging.Formatter):
    """
    A formatter that allows colors to be placed in the format string.
    Intended to help in creating more readable logging output.

    Based on https://github.com/borntyping/python-colorlog
    """

    def __init__(self,
                 fmt,
                 datefmt=None,
                 style='%',
                 log_colors=None,
                 reset=True,
                 secondary_log_colors=None):
        """
        Set the format and colors the ColouredFormatter will use.
        The ``fmt``, ``datefmt`` and ``style`` args are passed on to the
        ``logging.Formatter`` constructor.
        The ``secondary_log_colors`` argument can be used to create additional
        ``log_color`` attributes. Each key in the dictionary will set
        ``{key}_log_color``, using the value to select from a different
        ``log_colors`` set.
        :Parameters:
        - fmt (str): The format string to use
        - datefmt (str): A format string for the date
        - log_colors (dict):
            A mapping of log level names to color names
        - reset (bool):
            Implicitly append a color reset to all records unless False
        - style ('%' or '{' or '$'):
            The format style to use. (*No meaning prior to Python 3.2.*)
        - secondary_log_colors (dict):
            Map secondary ``log_color`` attributes. (*New in version 2.6.*)
        """
        super(ColouredFormatter, self).__init__(fmt, datefmt, style)

        self.log_colors = (log_colors
                           if log_colors is not None else DEFAULT_LOG_COLORS)
        self.secondary_log_colors = secondary_log_colors
        self.reset = reset

    def format(self, record):
        """Format a message from a record object."""
        record = ColoredRecord(record)
        record.log_color = escape_codes(self.log_colors, record.levelname)

        if self.secondary_log_colors:
            for name, log_colors in self.secondary_log_colors.items():
                color = escape_codes(log_colors, record.levelname)
                setattr(record, name + '_log_color', color)

        message = super(ColouredFormatter, self).format(record)

        if self.reset and not message.endswith(ESCAPE_CODES['reset']):
            message += ESCAPE_CODES['reset']

        return message


def get_logger(name, filename=None, datefmt=DATEFMT):
    """Helper function to get a logger.

    If a filename is specified, it will also log to that file."""
    if name in LOGGERS:
        return LOGGERS[name]
    logger = logging.getLogger(name)
    logger.propagate = False

    if supports_color():
        prefix_1, suffix = hash_coloured_escapes(name)
        prefix_2, _ = hash_coloured_escapes(name + 'salt')
    else:
        prefix_1, prefix_2, suffix = ('', '', '')

    date_str = '%(asctime)s ' if datefmt else ''

    stream_formatter = ColouredFormatter(
        '{}%(log_color)s%(levelname)-8s%(reset)s {}+{}+{} %(name)s'
        '%(log_color)s: %(message)s'.format(date_str, prefix_1, prefix_2,
                                            suffix),
        datefmt=datefmt)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

    if filename:
        file_handler = logging.FileHandler(filename)
        file_formatter = logging.Formatter(
            '{}|%(levelname)-8s %(name)s: %(message)s'.format(date_str))
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

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
            cprefix_1, csuffix = hash_coloured_escapes(name)
            cprefix_2, _ = hash_coloured_escapes(name + 'salt')
            name = cprefix_1 + '+' + cprefix_2 + '+' + csuffix + ' ' + name
        else:
            name = colored(name, color=color, ansi_code=ansi_code)

    prefix = name + ': '

    def printer(text):
        date = datetime.now().strftime(DATEFMT)
        print(date + ' ' + prefix + str(text))

    return printer

def escape_codes(log_colors, level_name):
    """Return escape codes from a ``log_colors`` dict."""
    return parse_colors(log_colors.get(level_name, ""))


def hash_coloured(text):
    """Return a ANSI coloured text based on its hash"""
    ansi_code = int(sha256(text.encode('utf-8')).hexdigest(), 16) % 230
    return colored(text, ansi_code=ansi_code)


def hash_coloured_escapes(text):
    """Return the ANSI hash colour prefix and suffix for a given text"""
    ansi_code = int(sha256(text.encode('utf-8')).hexdigest(), 16) % 230
    prefix, suffix = colored('SPLIT', ansi_code=ansi_code).split('SPLIT')
    return prefix, suffix
