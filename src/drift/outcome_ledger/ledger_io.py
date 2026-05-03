"""Re-export stub -- drift_session.outcome_ledger.ledger_io (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.outcome_ledger.ledger_io import (  # noqa: F401
    append_trajectory as append_trajectory,
)
from drift_session.outcome_ledger.ledger_io import (
    load_trajectories as load_trajectories,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.outcome_ledger.ledger_io")
