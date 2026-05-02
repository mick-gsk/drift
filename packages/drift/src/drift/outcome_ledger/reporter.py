"""Re-export stub -- drift_session.outcome_ledger.reporter (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.outcome_ledger.reporter import (  # noqa: F401
    render_markdown_report as render_markdown_report,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.outcome_ledger.reporter")
