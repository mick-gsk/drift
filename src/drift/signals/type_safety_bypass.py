"""Re-export stub -- drift_engine.signals.type_safety_bypass (ADR-100 Phase 3)."""

from drift_engine.signals.type_safety_bypass import (
    _DEFAULT_THRESHOLD as _DEFAULT_THRESHOLD,
)
from drift_engine.signals.type_safety_bypass import (
    _DOUBLE_CAST_ASSIGN_RE as _DOUBLE_CAST_ASSIGN_RE,
)
from drift_engine.signals.type_safety_bypass import (
    _EVENT_EMITTER_NON_NULL_RE as _EVENT_EMITTER_NON_NULL_RE,
)
from drift_engine.signals.type_safety_bypass import (
    _PLAYWRIGHT_LOCATOR_NON_NULL_RE as _PLAYWRIGHT_LOCATOR_NON_NULL_RE,
)
from drift_engine.signals.type_safety_bypass import (
    _SDK_IMPORT_RE as _SDK_IMPORT_RE,
)
from drift_engine.signals.type_safety_bypass import (
    _TS_DIRECTIVE_RE as _TS_DIRECTIVE_RE,
)
from drift_engine.signals.type_safety_bypass import (
    TypeSafetyBypassSignal as TypeSafetyBypassSignal,
)
from drift_engine.signals.type_safety_bypass import (
    _count_bypasses as _count_bypasses,
)
from drift_engine.signals.type_safety_bypass import (
    _effective_bypass_count as _effective_bypass_count,
)
from drift_engine.signals.type_safety_bypass import (
    _is_runtime_guarded_playwright_double_cast as _is_runtime_guarded_playwright_double_cast,
)
from drift_engine.signals.type_safety_bypass import (
    _read_source as _read_source,
)
