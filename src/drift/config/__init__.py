"""Configuration loading and validation for Drift.

This package re-exports every public symbol that was previously available
in the monolithic ``drift.config`` module.  All existing ``from drift.config
import X`` statements continue to work without modification.
"""

from drift.config._loader import (
    DriftConfig as DriftConfig,
)
from drift.config._loader import (
    _default_includes as _default_includes,
)
from drift.config._loader import (
    build_config_json_schema as build_config_json_schema,
)
from drift.config._schema import (
    AgentEffectivenessThresholds as AgentEffectivenessThresholds,
)
from drift.config._schema import (
    AgentObjective as AgentObjective,
)
from drift.config._schema import (
    AttributionConfig as AttributionConfig,
)
from drift.config._schema import (
    BriefConfig as BriefConfig,
)
from drift.config._schema import (
    CalibrationConfig as CalibrationConfig,
)
from drift.config._schema import (
    DeferredArea as DeferredArea,
)
from drift.config._schema import (
    DocImplDriftConfig as DocImplDriftConfig,
)
from drift.config._schema import (
    FindingContextPolicy as FindingContextPolicy,
)
from drift.config._schema import (
    FindingContextRule as FindingContextRule,
)
from drift.config._schema import (
    LanguagesConfig as LanguagesConfig,
)
from drift.config._schema import (
    LayerBoundary as LayerBoundary,
)
from drift.config._schema import (
    LazyImportRule as LazyImportRule,
)
from drift.config._schema import (
    PathOverride as PathOverride,
)
from drift.config._schema import (
    PerformanceConfig as PerformanceConfig,
)
from drift.config._schema import (
    PluginConfig as PluginConfig,
)
from drift.config._schema import (
    PolicyConfig as PolicyConfig,
)
from drift.config._schema import (
    RecommendationsConfig as RecommendationsConfig,
)
from drift.config._schema import (
    SignalWeights as SignalWeights,
)
from drift.config._schema import (
    ThresholdsConfig as ThresholdsConfig,
)
from drift.config._signals import (
    SIGNAL_ABBREV as SIGNAL_ABBREV,
)
from drift.config._signals import (
    apply_signal_filter as apply_signal_filter,
)
from drift.config._signals import (
    resolve_signal_names as resolve_signal_names,
)

__all__ = [
    # Schema models
    "LayerBoundary",
    "LazyImportRule",
    "PolicyConfig",
    "ThresholdsConfig",
    "SignalWeights",
    "PathOverride",
    "DeferredArea",
    "FindingContextRule",
    "FindingContextPolicy",
    "AgentEffectivenessThresholds",
    "AgentObjective",
    "BriefConfig",
    "PluginConfig",
    "DocImplDriftConfig",
    "LanguagesConfig",
    "PerformanceConfig",
    "CalibrationConfig",
    "RecommendationsConfig",
    "AttributionConfig",
    # Loader
    "DriftConfig",
    "build_config_json_schema",
    # Signal helpers
    "SIGNAL_ABBREV",
    "resolve_signal_names",
    "apply_signal_filter",
]
