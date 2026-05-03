"""Re-export stub -- drift_mcp.mcp_router_architecture (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_architecture import (
    run_compile_policy as run_compile_policy,
)
from drift_mcp.mcp_router_architecture import (
    run_generate_skills as run_generate_skills,
)
from drift_mcp.mcp_router_architecture import (  # noqa: F401
    run_steer as run_steer,
)
from drift_mcp.mcp_router_architecture import (
    run_suggest_rules as run_suggest_rules,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_architecture")
