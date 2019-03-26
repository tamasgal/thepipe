# -*- coding: utf-8 -*-
# Filename: tools.py
"""
Manipulating time and so...

"""
from contextlib import contextmanager
from datetime import datetime
import os
import re
import time
from timeit import default_timer as timer
import sys

try:
    import resource  # linux/macos
except ImportError:
    import psutil  # windows

__author__ = "Tamas Gal and Moritz Lotze"
__credits__ = ["Konstantin Lepa <konstantin.lepa@gmail.com> for termcolor"]
__license__ = "MIT"
__email__ = "tgal@km3net.de"


class Timer:
    """A very simple, accurate and easy to use timer context"""

    def __init__(self, message='It', precision=3, callback=print):
        self.message = message
        self.precision = precision
        self.callback = callback
        self._start = None
        self._start_cpu = None
        self._finish = None
        self._finish_cpu = None

    def __enter__(self):
        self.start()

    def __exit__(self, exit_type, value, traceback):
        self.stop()

    def start(self):
        """Starts the timers"""
        self._start = timer()
        self._start_cpu = time.process_time()

    def stop(self):
        """Stops the timer"""
        self._finish = timer()
        self._finish_cpu = time.process_time()
        if self.callback is not None:
            self.log()
        return self.seconds

    @property
    def seconds(self):
        """The elapsed time in seconds"""
        return self._finish - self._start

    @property
    def cpu_seconds(self):
        """The elapsed CPU time in seconds"""
        return self._finish_cpu - self._start_cpu

    def log(self):
        """Call the callback function with the logging message"""
        self.callback("{0} took {1:.{3}f}s (CPU {2:.{3}f}s).".format(
            self.message, self.seconds, self.cpu_seconds, self.precision))


class Cuckoo:
    "A timed callback caller, which only executes once in a given interval."

    def __init__(self, interval=0, callback=print):
        "Setup with interval in seconds and a callback function"
        self.interval = interval
        self.callback = callback
        self.timestamp = None

    def reset(self):
        "Reset the timestamp"
        self.timestamp = datetime.now()

    def _interval_reached(self):
        "Check if defined interval is reached"
        return (
            datetime.now() - self.timestamp).total_seconds() > self.interval

    def __call__(self, *args, **kwargs):
        "Only execute callback when interval is reached."
        if self.timestamp is None or self._interval_reached():
            self.callback(*args, **kwargs)
            self.reset()


@contextmanager
def ignored(*exceptions):
    """Ignore-context for a given list of exceptions.

    Example:
        with ignored(AttributeError):
            foo.a = 1

    """
    try:
        yield
    except exceptions:
        pass


def peak_memory_usage():
    """Return peak memory usage in MB"""
    if sys.platform.startswith('win'):
        p = psutil.Process()
        return p.memory_info().peak_wset / 1024 / 1024

    mem = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    factor_mb = 1 / 1024
    if sys.platform == 'darwin':
        factor_mb = 1 / (1024 * 1024)
    return mem * factor_mb


ATTRIBUTES = dict(
    list(
        zip([
            'bold', 'dark', '', 'underline', 'blink', '', 'reverse',
            'concealed'
        ], list(range(1, 9)))))
del ATTRIBUTES['']

ATTRIBUTES_RE = r'\033\[(?:%s)m' % '|'  \
                .join(['%d' % v for v in ATTRIBUTES.values()])

HIGHLIGHTS = dict(
    list(
        zip([
            'on_grey', 'on_red', 'on_green', 'on_yellow', 'on_blue',
            'on_magenta', 'on_cyan', 'on_white'
        ], list(range(40, 48)))))

HIGHLIGHTS_RE = r'\033\[(?:%s)m' % '|'  \
                .join(['%d' % v for v in HIGHLIGHTS.values()])

COLORS = dict(
    list(
        zip([
            'grey',
            'red',
            'green',
            'yellow',
            'blue',
            'magenta',
            'cyan',
            'white',
        ], list(range(30, 38)))))

COLORS_RE = r'\033\[(?:%s)m' % '|'.join(['%d' % v for v in COLORS.values()])

RESET = r'\033[0m'
RESET_RE = r'\033\[0m'


def colored(text, color=None, on_color=None, attrs=None, ansi_code=None):
    """Colorize text, while stripping nested ANSI color sequences.

    Author:  Konstantin Lepa <konstantin.lepa@gmail.com> / termcolor

    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.
    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.
    Available attributes:
        bold, dark, underline, blink, reverse, concealed.
    Example:
        colored('Hello, World!', 'red', 'on_grey', ['blue', 'blink'])
        colored('Hello, World!', 'green')
    """
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        if ansi_code is not None:
            return "\033[38;5;{}m{}\033[0m".format(ansi_code, text)
        fmt_str = '\033[%dm%s'
        if color is not None:
            text = re.sub(COLORS_RE + '(.*?)' + RESET_RE, r'\1', text)
            text = fmt_str % (COLORS[color], text)
        if on_color is not None:
            text = re.sub(HIGHLIGHTS_RE + '(.*?)' + RESET_RE, r'\1', text)
            text = fmt_str % (HIGHLIGHTS[on_color], text)
        if attrs is not None:
            text = re.sub(ATTRIBUTES_RE + '(.*?)' + RESET_RE, r'\1', text)
            for attr in attrs:
                text = fmt_str % (ATTRIBUTES[attr], text)
        return text + RESET
    else:
        return text


def cprint(text, color=None, on_color=None, attrs=None):
    """Print colorize text.

    Author:  Konstantin Lepa <konstantin.lepa@gmail.com> / termcolor

    It accepts arguments of print function.
    """
    print((colored(text, color, on_color, attrs)))


def isnotebook():
    """Check if running within a Jupyter notebook"""
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True  # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False


def supports_color():
    """Checks if the terminal supports color."""
    if isnotebook():
        return True
    supported_platform = sys.platform != 'win32' or 'ANSICON' in os.environ
    is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    if not supported_platform or not is_a_tty:
        return False

    return True
