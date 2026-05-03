"""Re-export stub -- drift_mcp.mcp_legacy (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_legacy import (  # noqa: F401
    run_task_claim as run_task_claim,
)
from drift_mcp.mcp_legacy import (
    run_task_complete as run_task_complete,
)
from drift_mcp.mcp_legacy import (
    run_task_release as run_task_release,
)
from drift_mcp.mcp_legacy import (
    run_task_renew as run_task_renew,
)
from drift_mcp.mcp_legacy import (
    run_task_status as run_task_status,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_legacy")
