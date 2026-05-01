"""Re-export stub -- canonical implementation lives in drift_session.scope_resolver."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_session.scope_resolver import *

_sys.modules[__name__] = _importlib.import_module("drift_session.scope_resolver")
