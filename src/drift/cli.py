"""Re-export stub -- drift_cli.cli (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.cli import (  # noqa: F401
    SuggestingGroup as SuggestingGroup,
)
from drift_cli.cli import (
    main as main,
)
from drift_cli.cli import (
    safe_main as safe_main,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.cli")
