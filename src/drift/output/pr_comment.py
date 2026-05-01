"""Re-export stub -- drift_output.pr_comment (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.pr_comment import *  # noqa: F401,F403

analysis_to_pr_comment: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.pr_comment")
