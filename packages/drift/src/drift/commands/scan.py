"""Re-export stub -- drift_cli.commands.scan (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.scan import (  # noqa: F401
    scan as scan,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.scan")
