"""Re-export stub -- drift_cli.commands.validate_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.validate_cmd import (  # noqa: F401
    validate as validate,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.validate_cmd")
