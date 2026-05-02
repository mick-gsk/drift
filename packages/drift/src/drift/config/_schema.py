"""Thin backward-compat wrapper -- real implementation lives in drift_config._schema."""

from drift_config._schema import *  # noqa: F401, F403
from drift_config._schema import (
    AgentEffectivenessThresholds as AgentEffectivenessThresholds,
)
from drift_config._schema import (
    AgentObjective as AgentObjective,
)
from drift_config._schema import (
    AttributionConfig as AttributionConfig,
)
from drift_config._schema import (
    BriefConfig as BriefConfig,
)
from drift_config._schema import (
    CalibrationConfig as CalibrationConfig,
)
from drift_config._schema import (
    DeferredArea as DeferredArea,
)
from drift_config._schema import (
    DocImplDriftConfig as DocImplDriftConfig,
)
from drift_config._schema import (
    FindingContextPolicy as FindingContextPolicy,
)
from drift_config._schema import (
    FindingContextRule as FindingContextRule,
)
from drift_config._schema import (
    GateConfig as GateConfig,
)
from drift_config._schema import (
    GradeBandConfig as GradeBandConfig,
)
from drift_config._schema import (
    GuidedThresholds as GuidedThresholds,
)
from drift_config._schema import (
    IntegrationConfig as IntegrationConfig,
)
from drift_config._schema import (
    IntegrationSeverityMap as IntegrationSeverityMap,
)
from drift_config._schema import (
    IntegrationsGlobalConfig as IntegrationsGlobalConfig,
)
from drift_config._schema import (
    LanguagesConfig as LanguagesConfig,
)
from drift_config._schema import (
    LayerBoundary as LayerBoundary,
)
from drift_config._schema import (
    LazyImportRule as LazyImportRule,
)
from drift_config._schema import (
    PathOverride as PathOverride,
)
from drift_config._schema import (
    PerformanceConfig as PerformanceConfig,
)
from drift_config._schema import (
    PluginConfig as PluginConfig,
)
from drift_config._schema import (
    PolicyConfig as PolicyConfig,
)
from drift_config._schema import (
    RecommendationsConfig as RecommendationsConfig,
)
from drift_config._schema import (
    ScoringConfig as ScoringConfig,
)
from drift_config._schema import (
    SignalWeights as SignalWeights,
)
from drift_config._schema import (
    ThresholdsConfig as ThresholdsConfig,
)
from drift_config._schema import (
    TrendGateConfig as TrendGateConfig,
)
