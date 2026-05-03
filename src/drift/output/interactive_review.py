"""Re-export stub -- drift_output.interactive_review (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.interactive_review import *  # noqa: F401,F403

review_findings: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.interactive_review")
