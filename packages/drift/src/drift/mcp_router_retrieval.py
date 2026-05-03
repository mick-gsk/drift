"""Re-export stub -- drift_mcp.mcp_router_retrieval (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_retrieval")

# mypy-visible re-exports (runtime aliasing above is invisible to static analysis)
from drift.retrieval.mcp import (  # noqa: E402, F401
    run_cite,
    run_retrieve,
)
