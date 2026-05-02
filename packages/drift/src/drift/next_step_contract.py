"""Re-export stub -- canonical implementation lives in drift_session.next_step_contract."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_session.next_step_contract import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_session.next_step_contract import (
    _error_response as _error_response,
)
from drift_session.next_step_contract import (
    _next_step_contract as _next_step_contract,
)
from drift_session.next_step_contract import (
    _tool_call as _tool_call,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.next_step_contract")
