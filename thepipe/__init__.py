from pkg_resources import get_distribution, DistributionNotFound

version = get_distribution(__name__).version

from .core import Blob, Module, Pipeline
from .provenance import Provenance


Provenance()  # automatic provenance tracking by default
