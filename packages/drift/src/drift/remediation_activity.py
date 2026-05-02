"""Re-export stub -- canonical implementation lives in drift_session.remediation_activity."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_session.remediation_activity import *

_sys.modules[__name__] = _importlib.import_module("drift_session.remediation_activity")
