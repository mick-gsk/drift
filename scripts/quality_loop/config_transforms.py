"""Config-space transforms for MCTS-based drift config optimization.

Each ``ConfigAction`` wraps a single deterministic mutation of a
``DriftConfig`` (via Pydantic ``model_copy``).  All transforms return a
new config object; the original is never mutated.

The module exports ``ALL_TRANSFORMS``, a flat list consumed by
``ConfigMCTSSearch``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from drift.config import DriftConfig


@dataclass(frozen=True)
class ConfigAction:
    """A named, reversible config mutation."""

    name: str
    _fn: Callable[[DriftConfig], DriftConfig]

    def apply(self, config: DriftConfig) -> DriftConfig:
        """Return a new config with the transform applied."""
        return self._fn(config)


# ---------------------------------------------------------------------------
# Helper: create a new config with a single threshold field changed
# ---------------------------------------------------------------------------


def _with_threshold(field: str, delta: float | int) -> Callable[[DriftConfig], DriftConfig]:
    def _apply(config: DriftConfig) -> DriftConfig:
        current = getattr(config.thresholds, field)
        updated = type(current)(current + delta)
        new_thresh = config.thresholds.model_copy(update={field: updated})
        return config.model_copy(update={"thresholds": new_thresh})

    return _apply


def _with_weight(field: str, delta: float) -> Callable[[DriftConfig], DriftConfig]:
    def _apply(config: DriftConfig) -> DriftConfig:
        current = getattr(config.weights, field)
        updated = max(0.0, round(current + delta, 4))
        new_weights = config.weights.model_copy(update={field: updated})
        return config.model_copy(update={"weights": new_weights})

    return _apply


# ---------------------------------------------------------------------------
# Threshold transforms
# ---------------------------------------------------------------------------

ALL_TRANSFORMS: list[ConfigAction] = [
    # similarity_threshold (MDS)
    ConfigAction("similarity_threshold+0.05", _with_threshold("similarity_threshold", 0.05)),
    ConfigAction("similarity_threshold-0.05", _with_threshold("similarity_threshold", -0.05)),
    ConfigAction("similarity_threshold+0.10", _with_threshold("similarity_threshold", 0.10)),
    ConfigAction("similarity_threshold-0.10", _with_threshold("similarity_threshold", -0.10)),
    # high_complexity (PFS / CXS)
    ConfigAction("high_complexity+2", _with_threshold("high_complexity", 2)),
    ConfigAction("high_complexity-2", _with_threshold("high_complexity", -2)),
    # min_function_loc (PFS)
    ConfigAction("min_function_loc+3", _with_threshold("min_function_loc", 3)),
    ConfigAction("min_function_loc-3", _with_threshold("min_function_loc", -3)),
    # cxs_max_complexity
    ConfigAction("cxs_max_complexity+2", _with_threshold("cxs_max_complexity", 2)),
    ConfigAction("cxs_max_complexity-2", _with_threshold("cxs_max_complexity", -2)),
    # foe_max_imports (FOE)
    ConfigAction("foe_max_imports+3", _with_threshold("foe_max_imports", 3)),
    ConfigAction("foe_max_imports-3", _with_threshold("foe_max_imports", -3)),
    # tpd_min_test_functions (TPD)
    ConfigAction("tpd_min_test_functions+2", _with_threshold("tpd_min_test_functions", 2)),
    ConfigAction("tpd_min_test_functions-2", _with_threshold("tpd_min_test_functions", -2)),
    # recency_days (TV)
    ConfigAction("recency_days+7", _with_threshold("recency_days", 7)),
    ConfigAction("recency_days-7", _with_threshold("recency_days", -7)),
    # volatility_z_threshold (TV)
    ConfigAction("volatility_z_threshold+0.25", _with_threshold("volatility_z_threshold", 0.25)),
    ConfigAction("volatility_z_threshold-0.25", _with_threshold("volatility_z_threshold", -0.25)),
    # gcd_min_public_functions (GCD)
    ConfigAction("gcd_min_public_functions+1", _with_threshold("gcd_min_public_functions", 1)),
    ConfigAction("gcd_min_public_functions-1", _with_threshold("gcd_min_public_functions", -1)),
    # ---------------------------------------------------------------------------
    # Weight transforms (core signals)
    # ---------------------------------------------------------------------------
    ConfigAction("w_pattern_fragmentation+0.02", _with_weight("pattern_fragmentation", 0.02)),
    ConfigAction("w_pattern_fragmentation-0.02", _with_weight("pattern_fragmentation", -0.02)),
    ConfigAction("w_architecture_violation+0.02", _with_weight("architecture_violation", 0.02)),
    ConfigAction("w_architecture_violation-0.02", _with_weight("architecture_violation", -0.02)),
    ConfigAction("w_mutant_duplicate+0.02", _with_weight("mutant_duplicate", 0.02)),
    ConfigAction("w_mutant_duplicate-0.02", _with_weight("mutant_duplicate", -0.02)),
    ConfigAction("w_explainability_deficit+0.01", _with_weight("explainability_deficit", 0.01)),
    ConfigAction("w_explainability_deficit-0.01", _with_weight("explainability_deficit", -0.01)),
]
