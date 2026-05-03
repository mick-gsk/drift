"""Re-export stub -- drift_session.outcome_tracker (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.outcome_tracker import (  # noqa: F401
    Outcome as Outcome,
)
from drift_session.outcome_tracker import (
    OutcomeTracker as OutcomeTracker,
)
from drift_session.outcome_tracker import (
    compute_fingerprint as compute_fingerprint,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.outcome_tracker")
