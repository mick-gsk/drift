"""Re-export stub -- drift_output.github_format (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.github_format import *  # noqa: F401,F403

findings_to_github_annotations: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.github_format")
