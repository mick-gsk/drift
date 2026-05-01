"""Re-export stub -- drift_cli.commands.patterns (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.patterns import (  # noqa: F401
    patterns as patterns,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.patterns")
