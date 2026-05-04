"""Re-export stub -- drift_cli.commands.badge (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.badge import (  # noqa: F401
    badge as badge,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.badge")
