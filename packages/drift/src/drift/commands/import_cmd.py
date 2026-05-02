"""Re-export stub -- drift_cli.commands.import_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.import_cmd import (  # noqa: F401
    import_report as import_report,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.import_cmd")
