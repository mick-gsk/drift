"""Re-export stub -- drift_mcp.mcp_router_repair (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_repair import (
    run_fix_apply as run_fix_apply,
)
from drift_mcp.mcp_router_repair import (  # noqa: F401
    run_fix_plan as run_fix_plan,
)
from drift_mcp.mcp_router_repair import (
    run_verify as run_verify,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_repair")
