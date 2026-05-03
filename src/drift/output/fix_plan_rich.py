"""Re-export stub -- drift_output.fix_plan_rich (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.fix_plan_rich import *  # noqa: F401,F403

render_fix_plan: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.fix_plan_rich")
