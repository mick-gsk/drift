"""Re-export stub -- drift_cli.commands.start (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.start import (  # noqa: F401
    start as start,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.start")
