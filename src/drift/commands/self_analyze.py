"""Re-export stub -- drift_cli.commands.self_analyze (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.self_analyze import (  # noqa: F401
    self_analyze as self_analyze,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.self_analyze")
