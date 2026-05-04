"""Re-export stub -- drift_mcp.mcp_orchestration (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_orchestration import (  # noqa: F401
    session_call_lock as session_call_lock,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_orchestration")
