"""Re-export stub -- drift_cli.commands.intent_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.intent_cmd import (  # noqa: F401
    intent as intent,
)
from drift_cli.commands.intent_cmd import (
    intent_list as intent_list,
)
from drift_cli.commands.intent_cmd import (
    intent_run as intent_run,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.intent_cmd")
