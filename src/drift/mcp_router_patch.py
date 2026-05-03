"""Re-export stub -- drift_mcp.mcp_router_patch (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_patch import (  # noqa: F401
    run_patch_begin as run_patch_begin,
)
from drift_mcp.mcp_router_patch import (
    run_patch_check as run_patch_check,
)
from drift_mcp.mcp_router_patch import (
    run_patch_commit as run_patch_commit,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_patch")
