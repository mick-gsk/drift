"""Re-export stub -- drift_cli.commands.context_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.context_cmd import (  # noqa: F401
    context as context,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.context_cmd")
