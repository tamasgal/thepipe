#!/usr/bin/env python3
from datetime import datetime
import json
import os
import platform
import psutil
import pytz
import sys
import types
import uuid

from .tools import peak_memory_usage

ENV_VARS_TO_LOG = [
    "PATH",
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "USER",
    "HOME",
    "SHELL",
    "VIRTUAL_ENV",
    "CONDA_DEFAULT_ENV",
    "CONDA_PREFIX",
    "CONDA_EXE",
    "CONDA_PROMOMPT_MODIFIER",
    "CONDA_SHLVL",
]


def imported_modules():
    """All imported modules"""
    for name, val in globals().items():
        if isinstance(val, types.ModuleType):
            yield val


def module_version(module):
    try:
        return module.__version__
    except AttributeError:
        try:
            return module.version
        except AttributeError:
            return "unknown"


def _getenv():
    return {var: os.getenv(var) for var in ENV_VARS_TO_LOG}


class Singleton(type):
    """Singleton metaclass"""

    instance = None

    def __call__(cls, *args, **kwargs):
        if not cls.instance:
            cls.instance = super().__call__(*args, **kwargs)
        return cls.instance


class Provenance(metaclass=Singleton):
    """
    The provenance manager.
    """

    def __init__(self):
        self._activities = []

    def start_activity(self, name):
        activity = Activity(name)
        activity.start()


class Activity:
    def __init__(self, name):
        self.name = name
        self._data = dict(
            uuid=str(uuid.uuid4()),
            name=name,
            start={},
            stop={},
            system={},
            input=[],
            output=[],
            samples=[],
        )


def isotime(timestamp):
    """ISO 8601 formatted date in UTC from unix timestamp"""
    return datetime.fromtimestamp(timestamp, pytz.utc).isoformat()


def now():
    """Returns the ISO 8601 formatted time in UTC"""
    return datetime.now(pytz.utc).isoformat()


def _system_load():
    """CPU and memory status"""
    return dict(peak_memory=peak_memory_usage())


def _system_provenance():
    """Provenance information of the system configuration"""

    bits, linkage = platform.architecture()

    return dict(
        executable=sys.executable,
        platform=dict(
            architecture_bits=bits,
            architecture_linkage=linkage,
            machine=platform.machine(),
            processor=platform.processor(),
            node=platform.node(),
            version=platform.version(),
            system=platform.system(),
            release=platform.release(),
            libcver=platform.libc_ver(),
            num_cpus=psutil.cpu_count(),
            boot_time=isotime(psutil.boot_time()),
        ),
        python=dict(
            version_string=sys.version,
            version=platform.python_version_tuple(),
            compiler=platform.python_compiler(),
            implementation=platform.python_implementation(),
        ),
        environment=_getenv(),
        arguments=sys.argv,
        start_time_utc=now(),
    )
