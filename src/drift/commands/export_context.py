"""Re-export stub -- drift_cli.commands.export_context (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.export_context import (  # noqa: F401
    export_context as export_context,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.export_context")
