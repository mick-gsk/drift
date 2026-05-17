"""Re-export stub -- drift_cli.commands.config_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.config_cmd import (  # noqa: F401
    config as config,
)
from drift_cli.commands.config_cmd import (
    schema as schema,
)
from drift_cli.commands.config_cmd import (
    show as show,
)
from drift_cli.commands.config_cmd import (
    validate as validate,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.config_cmd")
