"""Re-export stub -- drift_session.outcome_ledger.correlator (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.outcome_ledger.correlator import (  # noqa: F401
    classify_direction as classify_direction,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.outcome_ledger.correlator")
