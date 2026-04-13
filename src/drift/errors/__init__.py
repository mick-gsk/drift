"""Structured error codes and exception hierarchy for Drift.

This package re-exports every public symbol that was previously available
in the monolithic ``drift.errors`` module.  All existing ``from drift.errors
import X`` statements continue to work without modification.
"""

from drift.errors._codes import (
    ERROR_EXPLAIN_DEFAULTS as ERROR_EXPLAIN_DEFAULTS,
)
from drift.errors._codes import (
    ERROR_REGISTRY as ERROR_REGISTRY,
)
from drift.errors._codes import (
    EXIT_ANALYSIS_ERROR as EXIT_ANALYSIS_ERROR,
)
from drift.errors._codes import (
    EXIT_CONFIG_ERROR as EXIT_CONFIG_ERROR,
)
from drift.errors._codes import (
    EXIT_FINDINGS_ABOVE_THRESHOLD as EXIT_FINDINGS_ABOVE_THRESHOLD,
)
from drift.errors._codes import (
    EXIT_INTERRUPTED as EXIT_INTERRUPTED,
)
from drift.errors._codes import (
    EXIT_OK as EXIT_OK,
)
from drift.errors._codes import (
    EXIT_SYSTEM_ERROR as EXIT_SYSTEM_ERROR,
)
from drift.errors._codes import (
    ErrorInfo as ErrorInfo,
)
from drift.errors._codes import (
    _format_template_with_defaults as _format_template_with_defaults,
)
from drift.errors._codes import (
    format_error_info_for_explain as format_error_info_for_explain,
)
from drift.errors._exceptions import (
    DriftAnalysisError as DriftAnalysisError,
)
from drift.errors._exceptions import (
    DriftConfigError as DriftConfigError,
)
from drift.errors._exceptions import (
    DriftError as DriftError,
)
from drift.errors._exceptions import (
    DriftSystemError as DriftSystemError,
)
from drift.errors._exceptions import (
    _find_yaml_line as _find_yaml_line,
)
from drift.errors._exceptions import (
    yaml_context_snippet as yaml_context_snippet,
)

__all__ = [
    # Exit codes
    "EXIT_OK",
    "EXIT_FINDINGS_ABOVE_THRESHOLD",
    "EXIT_CONFIG_ERROR",
    "EXIT_ANALYSIS_ERROR",
    "EXIT_SYSTEM_ERROR",
    "EXIT_INTERRUPTED",
    # Error info
    "ErrorInfo",
    "ERROR_REGISTRY",
    "ERROR_EXPLAIN_DEFAULTS",
    "format_error_info_for_explain",
    # Exceptions
    "DriftError",
    "DriftConfigError",
    "DriftSystemError",
    "DriftAnalysisError",
    # YAML helpers
    "yaml_context_snippet",
    "_find_yaml_line",
]
