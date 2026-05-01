"""Re-export stub -- drift_cli.commands.serve (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.serve import (  # noqa: F401
    serve as serve,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.serve")
