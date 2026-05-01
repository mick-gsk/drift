"""Re-export stub -- drift_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output import *  # noqa: F401,F403

_sys.modules[__name__] = _importlib.import_module("drift_output")
