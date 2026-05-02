"""Re-export stub -- drift_mcp.mcp_router_analysis (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_analysis import (
    run_brief as run_brief,
)
from drift_mcp.mcp_router_analysis import (
    run_diff as run_diff,
)
from drift_mcp.mcp_router_analysis import (
    run_explain as run_explain,
)
from drift_mcp.mcp_router_analysis import (
    run_negative_context as run_negative_context,
)
from drift_mcp.mcp_router_analysis import (
    run_nudge as run_nudge,
)
from drift_mcp.mcp_router_analysis import (  # noqa: F401
    run_scan as run_scan,
)
from drift_mcp.mcp_router_analysis import (
    run_shadow_verify as run_shadow_verify,
)
from drift_mcp.mcp_router_analysis import (
    run_validate as run_validate,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_analysis")
