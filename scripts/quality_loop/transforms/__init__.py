"""Transform registry and public API for quality_loop transforms."""

from __future__ import annotations

from scripts.quality_loop.transforms.base import (
    ApplyResult,
    BaseTransform,
    RiskLevel,
    apply_transform,
)
from scripts.quality_loop.transforms.control_flow import (
    FlattenNestedIf,
    SimplifyBooleanReturn,
)
from scripts.quality_loop.transforms.dead_code import (
    RemoveDeadBranch,
    RemoveEmptyExcept,
)
from scripts.quality_loop.transforms.imports import (
    RemoveUnusedImports,
    SortImports,
)
from scripts.quality_loop.transforms.style import (
    FstringConversion,
    RemoveRedundantParens,
)
from scripts.quality_loop.transforms.variables import (
    ExtractRepeatedLiteral,
    InlineOneTimeVariable,
)

# Default registry — transforms included in MCTS/GA search space.
# FstringConversion is risk_level="medium" and opt-in only; excluded by default.
TRANSFORMS: list[type[BaseTransform]] = [
    RemoveUnusedImports,
    SortImports,
    InlineOneTimeVariable,
    FlattenNestedIf,
    SimplifyBooleanReturn,
    RemoveRedundantParens,
    RemoveDeadBranch,
    RemoveEmptyExcept,
]

# All transforms including medium-risk opt-ins
ALL_TRANSFORMS: list[type[BaseTransform]] = TRANSFORMS + [
    FstringConversion,
    ExtractRepeatedLiteral,
]

__all__ = [
    "TRANSFORMS",
    "ALL_TRANSFORMS",
    "ApplyResult",
    "BaseTransform",
    "RiskLevel",
    "apply_transform",
    # Individual transforms
    "RemoveUnusedImports",
    "SortImports",
    "InlineOneTimeVariable",
    "ExtractRepeatedLiteral",
    "FlattenNestedIf",
    "SimplifyBooleanReturn",
    "RemoveRedundantParens",
    "FstringConversion",
    "RemoveDeadBranch",
    "RemoveEmptyExcept",
]
