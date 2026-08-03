from importlib.metadata import PackageNotFoundError, version as _version

try:
    version = _version(__name__)
except PackageNotFoundError:
    version = "unknown"

from .core import Blob, Module, Pipeline
from .provenance import Provenance


Provenance()  # automatic provenance tracking by default
