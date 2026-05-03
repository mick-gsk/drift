"""Re-export stub -- drift_mcp.mcp_catalog (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_catalog import (  # noqa: F401
    get_tool_catalog as get_tool_catalog,
)
from drift_mcp.mcp_catalog import (
    get_tool_catalog_error as get_tool_catalog_error,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_catalog")
