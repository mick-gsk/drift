"""Re-export stub -- drift_mcp.mcp_utils (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_utils import (  # noqa: F401
    logger as logger,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_utils")
