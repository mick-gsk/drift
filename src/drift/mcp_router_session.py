"""Re-export stub -- drift_mcp.mcp_router_session (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_session import (
    run_map as run_map,
)
from drift_mcp.mcp_router_session import (
    run_session_end as run_session_end,
)
from drift_mcp.mcp_router_session import (  # noqa: F401
    run_session_start as run_session_start,
)
from drift_mcp.mcp_router_session import (
    run_session_status as run_session_status,
)
from drift_mcp.mcp_router_session import (
    run_session_trace as run_session_trace,
)
from drift_mcp.mcp_router_session import (
    run_session_update as run_session_update,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_session")
