"""Re-export stub -- drift_output.markdown_report (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.markdown_report import *  # noqa: F401,F403

analysis_to_markdown: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.markdown_report")
