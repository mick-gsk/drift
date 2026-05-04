"""Re-export stub -- drift_cli.commands.patch_cmd (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.patch_cmd import (
    begin as begin,
)
from drift_cli.commands.patch_cmd import (
    check as check,
)
from drift_cli.commands.patch_cmd import (
    commit as commit,
)
from drift_cli.commands.patch_cmd import (  # noqa: F401
    patch as patch,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.patch_cmd")
