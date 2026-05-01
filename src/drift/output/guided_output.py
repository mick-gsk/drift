"""Re-export stub -- drift_output.guided_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.guided_output import (  # noqa: F401
    can_continue,
    determine_status,
    emoji_for_status,
    headline_for_status,
    is_calibrated,
    plain_text_for_signal,
    profile_score_context,
    severity_label,
)

_sys.modules[__name__] = _importlib.import_module("drift_output.guided_output")
