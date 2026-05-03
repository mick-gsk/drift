"""Re-export stub -- canonical implementation lives in drift_output.finding_priority."""
# ruff: noqa: F401, F403, E501

import importlib as _importlib
import sys as _sys

from drift_output.finding_priority import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_output.finding_priority import _composite_sort_key as _composite_sort_key
from drift_output.finding_priority import _dedupe_findings as _dedupe_findings
from drift_output.finding_priority import (
    _expected_benefit_for_finding as _expected_benefit_for_finding,
)
from drift_output.finding_priority import _next_step_for_finding as _next_step_for_finding
from drift_output.finding_priority import _priority_class as _priority_class
from drift_output.finding_priority import generate_recommendation as generate_recommendation

_sys.modules[__name__] = _importlib.import_module("drift_output.finding_priority")
