#!/usr/bin/env python3
from datetime import datetime
from importlib import import_module
import json
import os
import platform
import psutil
import pytz
import sys
import types
import uuid

from pip._internal.operations import freeze

from .logger import get_logger
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

ENV_VARS_IN_CI_TO_LOG = [
    "APPVEYOR",
    "CI",
    "CIRCLECI",
    "CONTINUOUS_INTEGRATION",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "TF_BUILD",
    "TRAVIS",
]

log = get_logger("Provenance")


def python_packages():
    """All installed Python packages"""
    packages = []
    for entry in freeze.freeze(exclude_editable=True):
        name, version = entry.split("==")
        packages.append(dict(name=name, version=version))
    return packages


def _getenv():
    """Returns the environment variables while maskng sensitive data"""
    env = {var: os.getenv(var) for var in ENV_VARS_TO_LOG}
    for var in ENV_VARS_IN_CI_TO_LOG:
        value = os.getenv(var, "").lower()
        if value in ["", None]:
            env[var] = None
        elif os.getenv(var) in ["true", "t", "yes", "y", "1"]:
            env[var] = "true"
        elif os.getenv(var) in ["false", "f", "no", "n", "0"]:
            env[var] = "false"
        else:
            env[var] = "other"
    return env


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
        log.info("Initialising provenance tracking")
        self._activities = []
        self._backlog = []

    def start_activity(self, name):
        log.info("Starting activity '{}'".format(name))
        self._activities.append(Activity(name))

    def finish_activity(self):
        try:
            activity = self._activities.pop()
        except IndexError:
            log.error("There is no activity to finish.")
            return
        else:
            log.info("Finishing activity '{}'".format(activity.name))
            activity.finish()
            self._backlog.append(activity)

    @property
    def provenance(self):
        return [a.provenance for a in self._backlog]

    def as_json(self, **kwargs):
        """Dump provenance as JSON string. `kwargs` are passed to `json.dumps`"""
        return json.dumps(self.provenance, **kwargs)

    def reset(self):
        log.info("Resetting provenance")
        self._activities = []
        self._backlog = []


class Activity:
    def __init__(self, name):
        self.name = name
        self._data = dict(
            uuid=str(uuid.uuid4()),
            name=name,
            start=system_state(),
            stop={},
            system=system_provenance(),
            input=[],
            output=[],
            samples=[],
        )

    def finish(self):
        self._data["stop"] = system_state()

    @property
    def provenance(self):
        return self._data


def isotime(timestamp):
    """ISO 8601 formatted date in UTC from unix timestamp"""
    return datetime.fromtimestamp(timestamp, pytz.utc).isoformat()


def now():
    """Returns the ISO 8601 formatted time in UTC"""
    return datetime.now(pytz.utc).isoformat()


def system_state():
    return dict(time_utc=now(), peak_memory=peak_memory_usage())


def system_provenance():
    """Provenance information of the system configuration"""

    bits, linkage = platform.architecture()

    return dict(
        thepipe_version=import_module("thepipe").version,
        executable=sys.executable,
        arguments=sys.argv,
        environment=_getenv(),
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
            packages=python_packages(),
        ),
        start_time_utc=now(),
    )
