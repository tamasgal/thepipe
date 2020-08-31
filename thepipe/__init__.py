from .__version__ import version
from .core import Blob, Module, Pipeline
from .provenance import Provenance


Provenance()  # automatic provenance tracking by default
