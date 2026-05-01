"""Re-export stub -- drift_output.pr_comment (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.pr_comment import analysis_to_pr_comment  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.pr_comment")
