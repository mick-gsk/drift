"""Re-export stub -- drift_output.agent_tasks (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.agent_tasks import (  # noqa: F401
    analysis_to_agent_tasks,
    analysis_to_agent_tasks_json,
)

_sys.modules[__name__] = _importlib.import_module("drift_output.agent_tasks")
