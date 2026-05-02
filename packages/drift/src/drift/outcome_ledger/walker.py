"""Re-export stub -- drift_session.outcome_ledger.walker (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.outcome_ledger.walker import (  # noqa: F401
    MergeCandidate as MergeCandidate,
)
from drift_session.outcome_ledger.walker import (
    walk_recent_merges as walk_recent_merges,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.outcome_ledger.walker")
