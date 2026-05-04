"""Re-export stub -- drift_output.interactive_review (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.interactive_review import review_findings  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.interactive_review")
