"""Re-export stub -- drift_output.prompt_generator (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.prompt_generator import *  # noqa: F401,F403

file_role_description: Any
generate_agent_prompt: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.prompt_generator")
