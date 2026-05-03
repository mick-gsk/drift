"""Re-export stub -- canonical implementation lives in drift_session.next_step_contract."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_session.next_step_contract import *

_sys.modules[__name__] = _importlib.import_module("drift_session.next_step_contract")
