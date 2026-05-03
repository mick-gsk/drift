"""Re-export stub -- canonical implementation lives in drift_engine.response_shaping."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.response_shaping import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_engine.response_shaping import SCHEMA_VERSION as SCHEMA_VERSION
from drift_engine.response_shaping import VALID_RESPONSE_PROFILES as VALID_RESPONSE_PROFILES
from drift_engine.response_shaping import _base_response as _base_response
from drift_engine.response_shaping import apply_output_mode as apply_output_mode
from drift_engine.response_shaping import build_drift_score_scope as build_drift_score_scope
from drift_engine.response_shaping import shape_for_profile as shape_for_profile

_sys.modules[__name__] = _importlib.import_module("drift_engine.response_shaping")
