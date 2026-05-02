"""Re-export stub -- canonical implementation lives in drift_session.next_step_contract."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_session.next_step_contract import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_session.next_step_contract import DONE_ACCEPT_CHANGE as DONE_ACCEPT_CHANGE
from drift_session.next_step_contract import DONE_DIFF_ACCEPT as DONE_DIFF_ACCEPT
from drift_session.next_step_contract import DONE_NO_FINDINGS as DONE_NO_FINDINGS
from drift_session.next_step_contract import DONE_NUDGE_SAFE as DONE_NUDGE_SAFE
from drift_session.next_step_contract import DONE_SAFE_TO_COMMIT as DONE_SAFE_TO_COMMIT
from drift_session.next_step_contract import DONE_STAGED_EXISTS as DONE_STAGED_EXISTS
from drift_session.next_step_contract import DONE_TASK_AND_NUDGE as DONE_TASK_AND_NUDGE
from drift_session.next_step_contract import DONE_TASKS_COMPLETE as DONE_TASKS_COMPLETE
from drift_session.next_step_contract import SCHEMA_VERSION as SCHEMA_VERSION
from drift_session.next_step_contract import _error_response as _error_response
from drift_session.next_step_contract import _next_step_contract as _next_step_contract
from drift_session.next_step_contract import _tool_call as _tool_call

_sys.modules[__name__] = _importlib.import_module("drift_session.next_step_contract")
