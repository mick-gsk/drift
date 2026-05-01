"""Re-export stub -- drift_session.session_handover (ADR-100 Phase 4b)."""

import importlib as _importlib
import sys as _sys

from drift_session.session_handover import (  # noqa: F401
    ChangeClass as ChangeClass,
)
from drift_session.session_handover import (
    PlaceholderFlag as PlaceholderFlag,
)
from drift_session.session_handover import (
    RequiredArtifact as RequiredArtifact,
)
from drift_session.session_handover import (
    ShapeError as ShapeError,
)
from drift_session.session_handover import (
    ValidationResult as ValidationResult,
)
from drift_session.session_handover import (
    classify_session as classify_session,
)
from drift_session.session_handover import (
    classify_touched as classify_touched,
)
from drift_session.session_handover import (
    detect_touched_files as detect_touched_files,
)
from drift_session.session_handover import (
    required_artifacts as required_artifacts,
)
from drift_session.session_handover import (
    validate as validate,
)
from drift_session.session_handover import (
    validate_bypass_reason as validate_bypass_reason,
)

_sys.modules[__name__] = _importlib.import_module("drift_session.session_handover")
