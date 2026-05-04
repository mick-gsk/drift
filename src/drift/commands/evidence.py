"""Re-export stub — drift_verify._cmd.evidence_cmd (ADR-100 pattern)."""

import importlib as _importlib
import sys as _sys

from drift_verify._cmd import evidence_cmd as evidence_cmd  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_verify._cmd")
