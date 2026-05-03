"""Re-export stub -- drift_output.badge_svg (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.badge_svg import *  # noqa: F401,F403

render_badge_svg: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.badge_svg")
