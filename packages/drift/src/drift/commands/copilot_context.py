"""Re-export stub -- drift_cli.commands.copilot_context (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.copilot_context import (  # noqa: F401
    copilot_context as copilot_context,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.copilot_context")
