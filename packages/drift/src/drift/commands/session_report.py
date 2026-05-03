"""Re-export stub -- drift_cli.commands.session_report (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.session_report import (  # noqa: F401
    session_report as session_report,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.session_report")
