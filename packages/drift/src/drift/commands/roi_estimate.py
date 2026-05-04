"""Re-export stub -- drift_cli.commands.roi_estimate (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.roi_estimate import (  # noqa: F401
    roi_estimate as roi_estimate,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.roi_estimate")
