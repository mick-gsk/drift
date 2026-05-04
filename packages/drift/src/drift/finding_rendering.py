"""Re-export stub -- canonical implementation lives in drift_output.finding_rendering."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_output.finding_rendering import *

# Explicit re-exports for mypy
from drift_output.finding_rendering import (
    _finding_guided as _finding_guided,
)
from drift_output.finding_rendering import (
    _priority_class as _priority_class,
)

_sys.modules[__name__] = _importlib.import_module("drift_output.finding_rendering")
