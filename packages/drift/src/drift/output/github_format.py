"""Re-export stub -- drift_output.github_format (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.github_format import findings_to_github_annotations  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.github_format")
