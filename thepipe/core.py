# -*- coding: utf-8 -*-
# Filename: core.py
"""
The core of thepipe framework.

"""
from collections import deque, OrderedDict
import inspect
import gzip
import signal
import os
import time
from timeit import default_timer as timer
import types

import toml
import numpy as np

from .tools import peak_memory_usage, ignored, Timer
from .logger import get_logger, get_printer

__author__ = "Tamas Gal"
__credits__ = ["Moritz Lotze", "Thomas Heid", "Johannes Schumann"]
__license__ = "MIT"
__email__ = "tgal@km3net.de"

STATS_LIMIT = 100000
MODULE_CONFIGURATION = 'pipeline.toml'
RESERVED_ARGS = set(['every', 'only_if', 'timeit'])


class Blob(OrderedDict):
    """A simple (ordered) dict with a fancy name. This should hold the data."""
    def __init__(self, *args, **kwargs):
        OrderedDict.__init__(self, *args, **kwargs)
        self.log = get_logger("Blob")

    def __str__(self):
        if not self:
            return "Empty blob"
        padding = max(len(k) for k in self.keys()) + 3
        output = ["Blob ({} entries):".format(len(self))]
        for key, value in self.items():
            output.append(" '{}'".format(key).ljust(padding) +
                          " => {}".format(repr(value)))
        return "\n".join(output)

    def __getitem__(self, key):
        try:
            val = OrderedDict.__getitem__(self, key)
        except KeyError:
            self.log.error("No key named '%s' found in Blob.\n"
                           "Available keys: %s" %
                           (key, ', '.join(self.keys())))
            raise
        return val


class Module:
    """The module which can be attached to the pipeline"""
    def __init__(self, name=None, **parameters):
        if name is None:
            name = self.__class__.__name__
        self._name = name
        self.services = ServiceManager()
        self.provided_services = {}
        self.required_services = {}
        self.parameters = parameters
        self._processed_parameters = []
        self.only_if = set()
        self.every = 1
        if self.__module__ == '__main__':
            self.logger_name = self.__class__.__name__
        else:
            self.logger_name = self.__module__ + '.' + self.__class__.__name__
        if name != self.logger_name:
            self.logger_name += '.{}'.format(name)
        self.log = get_logger(self.logger_name)
        self.log.debug("Initialising %s", name)
        self.log.debug("The logger is called '%s'", self.logger_name)
        self.cprint = get_printer(self.logger_name)
        self.timeit = self.get('timeit') or False
        self._timeit = {
            'process': deque(maxlen=100000),
            'process_cpu': deque(maxlen=100000),
            'finish': 0,
            'finish_cpu': 0
        }

        self.configure()

        self._check_unused_parameters()

    def configure(self):
        """Configure module, like instance variables etc."""

    def expose(self, obj, name):
        """Expose an object as a service to the Pipeline"""
        self.provided_services[name] = obj

    def print(self, *args, **kwargs):
        self.log.deprecation(
            "`Module.print` has been deprecated, please use `cprint` instead!")
        self.cprint(*args, **kwargs)

    @property
    def name(self):
        """The name of the module"""
        return self._name

    def add(self, name, value):
        """Add the parameter with the desired value to the dict"""
        self.parameters[name] = value

    def get(self, name, default=None):
        """Return the value of the requested parameter or `default` if None."""
        value = self.parameters.get(name)
        self._processed_parameters.append(name)
        if value is None:
            return default
        return value

    def require(self, name):
        """Return the value of the requested parameter or raise an error."""
        value = self.get(name)
        if value is None:
            raise TypeError("{0} requires the parameter '{1}'.".format(
                self.__class__, name))
        return value

    def require_service(self, name, why=''):
        """Add a service requirement with an optional reason"""
        self.required_services[name] = why

    def prepare(self):
        """Prepare! Executed between configure and the first process"""
        return

    def process(self, blob):  # pylint: disable=R0201
        """Knead the blob and return it"""
        return blob

    def finish(self):
        """Clean everything up."""
        return

    def pre_finish(self):
        """Do the last few things before calling finish()"""
        return self.finish()

    def open_file(self, filename, gzipped=False):
        """Open the file with filename"""
        try:
            if gzipped or filename.endswith('.gz'):
                return gzip.open(filename, 'rb')
            else:
                return open(filename, 'rb')
        except TypeError:
            self.log.error("Please specify a valid filename.")
            raise SystemExit
        except IOError as error_message:
            self.log.error(error_message)
            raise SystemExit

    def _check_unused_parameters(self):
        """Check if any of the parameters passed in are ignored"""
        all_params = set(self.parameters.keys())
        processed_params = set(self._processed_parameters)
        unused_params = all_params - processed_params - RESERVED_ARGS

        if unused_params:
            self.log.warning("The following parameters were ignored: %s",
                             ', '.join(sorted(unused_params)))

    def __call__(self, *args, **kwargs):
        """Run process if directly called."""
        self.log.info("Calling process")
        return self.process(*args, **kwargs)


class Pipeline:
    """The holy pipeline which holds everything together.

    If initialised with timeit=True, all modules will be monitored, otherwise
    only the overall statistics and modules with `timeit=True` will be
    shown.

    Parameters
    ----------
    timeit: bool, optional [default=False]
        Display time profiling statistics for the pipeline?
    configfile: str, optional [default='pipeline.toml']
        Path to a configuration file (TOML format) which contains parameters
        for attached modules.
    stats_limit: int, optional [default=100000]
        The number of cycles to keep track of when using `timeit=True`
    """
    def __init__(self,
                 blob=None,
                 timeit=False,
                 configfile=None,
                 stats_limit=100000):
        self.log = get_logger(self.__class__.__name__)
        self.cprint = get_printer(self.__class__.__name__)

        if configfile is None and os.path.exists(MODULE_CONFIGURATION):
            configfile = MODULE_CONFIGURATION

        self.load_configuration(configfile)

        self.init_timer = Timer("Pipeline and module initialisation")
        self.init_timer.start()

        self.modules = []
        self.services = ServiceManager()
        self.required_services = {}
        self.blob = blob or Blob()
        self.timeit = timeit
        self._timeit = {
            'init': timer(),
            'init_cpu': time.process_time(),
            'cycles': deque(maxlen=stats_limit),
            'cycles_cpu': deque(maxlen=stats_limit)
        }
        self._cycle_count = 0
        self._stop = False
        self._finished = False
        self.was_interrupted = False

    def load_configuration(self, configfile):
        if configfile is not None:
            self.cprint(
                "Reading module configuration from '{}'".format(configfile))
            self.log.warning(
                "Keep in mind that the module configuration file has "
                "precedence over keyword arguments in the attach method!")
            with open(configfile, 'r') as fobj:
                config = toml.load(fobj)
            variables = config.pop('VARIABLES', None)
            if variables is not None:
                for _, entries in config.items():
                    for key, value in entries.items():
                        print(key, value)
                        if value in variables:
                            entries[key] = variables[value]
        else:
            config = {}

        self.module_configuration = config

    def attach(self, module_factory, name=None, **kwargs):
        """Attach a module to the pipeline system"""
        fac = module_factory

        if name is None:
            name = fac.__name__

        self.log.info("Attaching module '{0}'".format(name))

        if (inspect.isclass(fac) and issubclass(fac, Module)) or \
                name == 'GenericPump':
            self.log.debug("Attaching as regular module")
            if name in self.module_configuration:
                self.log.debug(
                    "Applying pipeline configuration file for module '%s'" %
                    name)
                for key, value in self.module_configuration[name].items():
                    if key in kwargs:
                        self.log.info(
                            "Overwriting parameter '%s' in module '%s' from "
                            "the pipeline configuration file." % (key, name))
                    kwargs[key] = value
            module = fac(name=name, **kwargs)
            if hasattr(module, "provided_services"):
                for service_name, obj in module.provided_services.items():
                    self.services.register(service_name, obj)
            if hasattr(module, "required_services"):
                updated_required_services = {}
                updated_required_services.update(self.required_services)
                updated_required_services.update(module.required_services)
                self.required_services = updated_required_services
            module.services = self.services
        else:
            if isinstance(fac, types.FunctionType):
                self.log.debug("Attaching as function module")
            else:
                self.log.critical("Don't know how to attach module '{0}'!\n"
                                  "But I'll do my best".format(name))
            module = fac
            module.name = name
            module.timeit = self.timeit

        # Special parameters
        if 'only_if' in kwargs:
            required_keys = kwargs['only_if']
            if isinstance(required_keys, str):
                required_keys = [required_keys]
            module.only_if = set(required_keys)
        else:
            module.only_if = set()

        if 'blob_keys' in kwargs:
            module.blob_keys = kwargs['blob_keys']
        else:
            module.blob_keys = None

        if 'every' in kwargs:
            module.every = kwargs['every']
        else:
            module.every = 1

        self._timeit[module] = {
            'process': deque(maxlen=100000),
            'process_cpu': deque(maxlen=100000),
            'finish': 0,
            'finish_cpu': 0
        }

        self.modules.append(module)

    def _drain(self, cycles=None):
        """Activate the pump and let the flow go.

        This will call the process() method on each attached module until
        a StopIteration is raised, usually by a pump when it reached the EOF.

        A StopIteration is also raised when self.cycles was set and the
        number of cycles has reached that limit.

        """
        self.log.info("Now draining...")
        if not cycles:
            self.log.info(
                "No cycle count, the pipeline may be drained forever.")

        try:
            while not self._stop:
                cycle_start = timer()
                cycle_start_cpu = time.process_time()

                self.log.debug("Pumping blob #%d", self._cycle_count)
                self.blob = Blob()

                for module in self.modules:
                    if self.blob is None:
                        self.log.debug("Skipping %s, due to empty blob.",
                                       module.name)
                        continue
                    if module.only_if and not module.only_if.issubset(
                            set(self.blob.keys())):
                        self.log.debug(
                            "Skipping %s, due to missing required key"
                            "'%s'.", module.name, module.only_if)
                        continue

                    if (self._cycle_count + 1) % module.every != 0:
                        self.log.debug("Skipping %s (every %s iterations).",
                                       module.name, module.every)
                        continue

                    if module.blob_keys is not None:
                        blob_to_send = Blob({
                            k: self.blob[k]
                            for k in module.blob_keys if k in self.blob
                        })
                    else:
                        blob_to_send = self.blob

                    self.log.debug("Processing %s", module.name)
                    start = timer()
                    start_cpu = time.process_time()
                    new_blob = module(blob_to_send)
                    if self.timeit or module.timeit:
                        self._timeit[module]['process'] \
                            .append(timer() - start)
                        self._timeit[module]['process_cpu'] \
                            .append(time.process_time() - start_cpu)

                    if module.blob_keys is not None:
                        if new_blob is not None:
                            for key in new_blob.keys():
                                self.blob[key] = new_blob[key]
                    else:
                        self.blob = new_blob

                self._timeit['cycles'].append(timer() - cycle_start)
                self._timeit['cycles_cpu'].append(time.process_time() -
                                                  cycle_start_cpu)
                self._cycle_count += 1
                if cycles and self._cycle_count >= cycles:
                    raise StopIteration
        except StopIteration:
            self.log.info("Nothing left to pump through.")
        return self.finish()

    def _check_service_requirements(self):
        """Final comparison of provided and required modules"""
        missing = self.services.get_missing_services(
            self.required_services.keys())
        if missing:
            self.log.critical(
                "Following services are required and missing: %s",
                ', '.join(missing))
            return False
        return True

    def drain(self, cycles=None):
        """Execute _drain while trapping KeyboardInterrupt"""
        if not self._check_service_requirements():
            self.init_timer.stop()
            return self.finish()

        self.log.info("Preparing modules to process")
        for module in self.modules:
            if hasattr(module, 'prepare'):
                self.log.info("Preparing %s" % module.name)
                module.prepare()

        self.init_timer.stop()
        self.log.info("Trapping CTRL+C and starting to drain.")
        signal.signal(signal.SIGINT, self._handle_ctrl_c)
        with ignored(KeyboardInterrupt):
            return self._drain(cycles)

    def finish(self):
        """Call finish() on each attached module"""
        finish_blob = Blob()
        for module in self.modules:
            if hasattr(module, 'pre_finish'):
                self.log.info("Finishing %s" % module.name)
                start_time = timer()
                start_time_cpu = time.process_time()
                finish_blob[module.name] = module.pre_finish()
                self._timeit[module]['finish'] = timer() - start_time
                self._timeit[module]['finish_cpu'] = \
                    time.process_time() - start_time_cpu
            else:
                self.log.info("Skipping function module %s" % module.name)
        self._timeit['finish'] = timer()
        self._timeit['finish_cpu'] = time.process_time()
        self._print_timeit_statistics()
        self._finished = True

        return finish_blob

    def _handle_ctrl_c(self, *_):
        """Handle the keyboard interrupts."""
        if self._stop:
            print("\nForced shutdown...")
            raise SystemExit
        if not self._stop:
            hline = 42 * '='
            print('\n' + hline + "\nGot CTRL+C, waiting for current cycle...\n"
                  "Press CTRL+C again if you're in hurry!\n" + hline)
            self.was_interrupted = True
            self._stop = True

    def _print_timeit_statistics(self):

        if self._cycle_count < 1:
            return

        def calc_stats(values):
            """Return a tuple of statistical values"""
            return [f(values) for f in (np.mean, np.median, min, max, np.std)]

        def timef(seconds):
            """Return a string of formatted time value for given seconds"""
            elapsed_time = seconds
            if elapsed_time > 180:
                elapsed_time /= 60
                unit = 'min'
            else:
                unit = 's'
            return "{0:.6f}{1}".format(elapsed_time, unit)

        def statsf(prefix, values):
            stats = "  mean: {0}  medi: {1}  min: {2}  max: {3}  std: {4}"
            values = [timef(v) for v in values]
            return "  " + prefix + stats.format(*values)

        cycles = self._timeit['cycles']
        n_cycles = len(cycles)

        cycles_cpu = self._timeit['cycles_cpu']
        overall = self._timeit['finish'] - self._timeit['init']
        overall_cpu = self._timeit['finish_cpu'] - self._timeit['init_cpu']
        memory = peak_memory_usage()

        print(60 * '=')
        print("{0} cycles drained in {1} (CPU {2}). Memory peak: {3:.2f} MB".
              format(self._cycle_count, timef(overall), timef(overall_cpu),
                     memory))
        if self._cycle_count > n_cycles:
            print("Statistics are based on the last {0} cycles.".format(
                n_cycles))
        if cycles:
            print(statsf('wall', calc_stats(cycles)))
        if cycles_cpu:
            print(statsf('CPU ', calc_stats(cycles_cpu)))

        for module in self.modules:
            if not module.timeit and not self.timeit:
                continue
            finish_time = self._timeit[module]['finish']
            finish_time_cpu = self._timeit[module]['finish_cpu']
            process_times = self._timeit[module]['process']
            process_times_cpu = self._timeit[module]['process_cpu']
            print(module.name + " - process: {0:.3f}s (CPU {1:.3f}s)"
                  " - finish: {2:.3f}s (CPU {3:.3f}s)".format(
                      sum(process_times), sum(process_times_cpu), finish_time,
                      finish_time_cpu))
            if process_times:
                print(statsf('wall', calc_stats(process_times)))
            if process_times_cpu:
                print(statsf('CPU ', calc_stats(process_times_cpu)))


class ServiceManager:
    """
    Takes care of pipeline services.
    """
    def __init__(self):
        self._services = {}
        self.log = get_logger(self.__class__.__name__)

    def register(self, name, service):
        """
        Service registration

        Args:
            name: Name of the provided service
            service: Reference to the service
        """
        self._services[name] = service

    def get_missing_services(self, services):
        """
        Check if all required services are provided

        Args:
            services: List the service names which are required
        Returns:
            List with missing services
        """
        required_services = set(services)
        provided_services = set(self._services.keys())
        missing_services = required_services.difference(provided_services)

        return sorted(missing_services)

    def __getitem__(self, name):
        return self._services[name]

    def __getattr__(self, name):
        return self._service[name]

    def __contains__(self, name):
        return name in self._services
