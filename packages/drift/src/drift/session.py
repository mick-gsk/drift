"""Re-export stub -- drift_session.session (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.session import (  # noqa: F401
    DriftSession,
    OrchestrationMetrics,
    SessionManager,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.session")
