#!/usr/bin/env python3
"""
Provenance tracking inspired by the ctapipe approach.

"""
import atexit
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache
from importlib import import_module
import json
import os
import platform
import sys
import uuid
import psutil
import pytz

from pip._internal.operations import freeze
from dateutil.parser import isoparse

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


@lru_cache(maxsize=None)
def python_packages():
    """All installed Python packages.

    LRU cached, assuming no package installations during runtime.
    """
    packages = []
    for entry in freeze.freeze(exclude_editable=True):
        try:
            name, version = entry.split("==")
        except ValueError:
            pass
        else:
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
        self._outfile = None

        self._main_activity_uuid = self.start_activity("main session")

        atexit.register(self._export)

    @property
    def outfile(self):
        return self._outfile

    @outfile.setter
    def outfile(self, outfile):
        """The file to save the full provenance information"""
        if outfile is not None and os.path.exists(outfile):
            log.warning(
                "Provenance output file ({}) exists and will be overwritten upon exit.".format(
                    outfile
                )
            )
        self._outfile = outfile

    def start_activity(self, name):
        """Starts a new activity and returns its UUID for future reference"""
        log.info("Starting activity '{}'".format(name))
        activity = _Activity(name)
        if self._activities:
            activity._data["parent_activity"] = self.current_activity.uuid
            self.current_activity._data["child_activities"].append(activity.uuid)
        self._activities.append(activity)
        return activity.uuid

    def finish_activity(self, uuid, status="completed"):
        """Finishes an activity with the given UUID"""
        for idx, activity in enumerate(self._activities):
            if activity.uuid == uuid:
                self._activities.pop(idx)
                log.info("Finishing activity '{}'".format(activity.name))
                activity.finish(status)
                self._backlog.append(activity)
                break
        else:
            raise ValueError("Unable to finish activity, no matching UUID found.")

    def record_configuration(self, configuration):
        """Record configuration parameters (e.g. of the pipeline)"""
        self.current_activity.record_configuration(configuration)

    def record_input(self, url, comment=""):
        self.current_activity.record_input(url, comment)

    def record_output(self, url, comment=""):
        self.current_activity.record_output(url, comment)

    @property
    def current_activity(self):
        if not self._activities:
            self.start_activity(name=sys.executable)
        return self._activities[-1]

    @contextmanager
    def activity(self, name):
        activity_uuid = self.start_activity(name)
        yield
        self.finish_activity(activity_uuid)

    @property
    def provenance(self):
        return [a.provenance for a in self._backlog]

    @property
    def backlog(self):
        return self._backlog

    def as_json(self, **kwargs):
        """Dump provenance as JSON string. `kwargs` are passed to `json.dumps`"""
        def fallback(obj):
            """Objects which cannot be serialised"""
            if isinstance(obj, set):
                return list(obj)
            try:
                return obj.__class__.__name__ + " instance"
            except (AttributeError, ValueError, TypeError):
                pass

        return json.dumps(self.provenance, default=fallback, **kwargs)

    def _export(self):
        """Writes the provenance information into outfile

        This function is called automatically upon exit, no manual call is required.
        """
        if self.outfile is None:
            return
        try:
            self.finish_activity(self._main_activity_uuid)
        except ValueError:
            log.warning("Could not finish the main session.")
        print("Provenance information has been written to '{}'".format(self.outfile))
        with open(self.outfile, "w") as fobj:
            fobj.write(self.as_json(indent=2))

    def reset(self):
        log.info("Resetting provenance")
        self._activities = []
        self._backlog = []
        self.outfile = None


class _Activity:
    def __init__(self, name):
        self.name = name
        self._data = dict(
            uuid=str(uuid.uuid4()),
            name=name,
            parent_activity=None,
            child_activities=[],
            start=system_state(),
            stop={},
            system=system_provenance(),
            input=[],
            output=[],
            samples=[],
            status="unfinished",
            configuration={},
        )

    @property
    def uuid(self):
        return self._data["uuid"]

    def record_configuration(self, configuration):
        """Records or updates configuration"""
        self._data["configuration"].update(configuration)

    def record_input(self, url, comment):
        self._data["input"].append(dict(url=url, comment=comment))

    def record_output(self, url, comment):
        self._data["output"].append(dict(url=url, comment=comment))

    def finish(self, status):
        self._data["stop"] = system_state()
        self._data["status"] = status
        self._data["duration"] = duration(
            self._data["start"]["time_utc"], self._data["stop"]["time_utc"]
        )

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


def duration(start, stop):
    """Return the duration in seconds between two ISO 8601 time strings in"""
    return (isoparse(stop) - isoparse(start)).total_seconds()
