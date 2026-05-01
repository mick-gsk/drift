"""Re-export stub -- drift_output.session_renderer (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.session_renderer import *  # noqa: F401,F403

render_session_report: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.session_renderer")
