"""Re-export stub -- drift_cli.commands.feedback (ADR-100 Phase 5b)."""

import importlib as _importlib
import sys as _sys

from drift_cli.commands.feedback import (  # noqa: F401
    feedback as feedback,
)
from drift_cli.commands.feedback import (
    import_feedback as import_feedback,
)
from drift_cli.commands.feedback import (
    mark as mark,
)
from drift_cli.commands.feedback import (
    push as push,
)
from drift_cli.commands.feedback import (
    summary as summary,
)

_sys.modules[__name__] = _importlib.import_module("drift_cli.commands.feedback")
