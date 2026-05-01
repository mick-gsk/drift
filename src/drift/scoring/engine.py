"""Re-export stub -- drift_engine.scoring.engine (ADR-100 Phase 3)."""

from drift_engine.scoring.engine import (
    _BREADTH_CAP as _BREADTH_CAP,
)
from drift_engine.scoring.engine import (
    _DAMPENING_K as _DAMPENING_K,
)
from drift_engine.scoring.engine import (
    _GRADE_BANDS as _GRADE_BANDS,
)
from drift_engine.scoring.engine import (
    _SIGNAL_WEIGHT_KEYS as _SIGNAL_WEIGHT_KEYS,
)
from drift_engine.scoring.engine import (
    _project_bounded_simplex as _project_bounded_simplex,
)
from drift_engine.scoring.engine import (
    _severity_for_score as _severity_for_score,
)
from drift_engine.scoring.engine import (
    apply_path_overrides as apply_path_overrides,
)
from drift_engine.scoring.engine import (
    assign_impact_scores as assign_impact_scores,
)
from drift_engine.scoring.engine import (
    auto_calibrate_weights as auto_calibrate_weights,
)
from drift_engine.scoring.engine import (
    calibrate_weights as calibrate_weights,
)
from drift_engine.scoring.engine import (
    composite_score as composite_score,
)
from drift_engine.scoring.engine import (
    compute_module_scores as compute_module_scores,
)
from drift_engine.scoring.engine import (
    compute_signal_scores as compute_signal_scores,
)
from drift_engine.scoring.engine import (
    delta_gate_pass as delta_gate_pass,
)
from drift_engine.scoring.engine import (
    resolve_path_override as resolve_path_override,
)
from drift_engine.scoring.engine import (
    score_to_grade as score_to_grade,
)
from drift_engine.scoring.engine import (
    severity_gate_pass as severity_gate_pass,
)
