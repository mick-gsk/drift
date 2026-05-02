"""Re-export stub -- drift_cli.commands.fix_plan (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.fix_plan import (  # noqa: F401
    fix_plan as fix_plan,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.fix_plan")
