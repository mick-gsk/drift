"""Re-export stub -- drift_mcp.mcp_router_intent (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_intent import (  # noqa: F401
    run_capture_intent as run_capture_intent,
)
from drift_mcp.mcp_router_intent import (
    run_feedback_for_agent as run_feedback_for_agent,
)
from drift_mcp.mcp_router_intent import (
    run_verify_intent as run_verify_intent,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_intent")
