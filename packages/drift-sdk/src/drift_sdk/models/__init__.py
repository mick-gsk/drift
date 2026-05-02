"""Core data models for Drift analysis.

This package re-exports every public symbol that was previously available
in the monolithic ``drift.models`` module.  All existing ``from drift.models
import X`` statements continue to work without modification.
"""

from drift_sdk.models._agent import AgentTask as AgentTask
from drift_sdk.models._agent import ConsolidationGroup as ConsolidationGroup
from drift_sdk.models._context import NegativeContext as NegativeContext
from drift_sdk.models._enums import (
    OUTPUT_SCHEMA_VERSION as OUTPUT_SCHEMA_VERSION,
)
from drift_sdk.models._enums import (
    AgentActionType as AgentActionType,
)
from drift_sdk.models._enums import (
    AnalysisStatus as AnalysisStatus,
)
from drift_sdk.models._enums import (
    AutomationFit as AutomationFit,
)
from drift_sdk.models._enums import (
    ChangeScope as ChangeScope,
)
from drift_sdk.models._enums import (
    FindingStatus as FindingStatus,
)
from drift_sdk.models._enums import (
    NegativeContextCategory as NegativeContextCategory,
)
from drift_sdk.models._enums import (
    NegativeContextScope as NegativeContextScope,
)
from drift_sdk.models._enums import (
    PatternCategory as PatternCategory,
)
from drift_sdk.models._enums import (
    RegressionPattern as RegressionPattern,
)
from drift_sdk.models._enums import (
    RegressionReasonCode as RegressionReasonCode,
)
from drift_sdk.models._enums import (
    RepairLevel as RepairLevel,
)
from drift_sdk.models._enums import (
    RepairMaturity as RepairMaturity,
)
from drift_sdk.models._enums import (
    ReviewRisk as ReviewRisk,
)
from drift_sdk.models._enums import (
    Severity as Severity,
)
from drift_sdk.models._enums import (
    SignalType as SignalType,
)
from drift_sdk.models._enums import (
    TaskComplexity as TaskComplexity,
)
from drift_sdk.models._enums import (
    TrendDirection as TrendDirection,
)
from drift_sdk.models._enums import (
    VerificationStrength as VerificationStrength,
)
from drift_sdk.models._enums import (
    severity_for_score as severity_for_score,
)
from drift_sdk.models._findings import (
    AgentAction as AgentAction,
)
from drift_sdk.models._findings import (
    AgentTelemetry as AgentTelemetry,
)
from drift_sdk.models._findings import (
    AnalyzerWarning as AnalyzerWarning,
)
from drift_sdk.models._findings import (
    Finding as Finding,
)
from drift_sdk.models._findings import (
    LogicalLocation as LogicalLocation,
)
from drift_sdk.models._findings import (
    ModuleScore as ModuleScore,
)
from drift_sdk.models._findings import (
    RepoAnalysis as RepoAnalysis,
)
from drift_sdk.models._findings import (
    TrendContext as TrendContext,
)
from drift_sdk.models._git import (
    Attribution as Attribution,
)
from drift_sdk.models._git import (
    BlameLine as BlameLine,
)
from drift_sdk.models._git import (
    CommitInfo as CommitInfo,
)
from drift_sdk.models._git import (
    FileHistory as FileHistory,
)
from drift_sdk.models._parse import (
    ClassInfo as ClassInfo,
)
from drift_sdk.models._parse import (
    FileInfo as FileInfo,
)
from drift_sdk.models._parse import (
    FunctionInfo as FunctionInfo,
)
from drift_sdk.models._parse import (
    ImportInfo as ImportInfo,
)
from drift_sdk.models._parse import (
    ParseResult as ParseResult,
)
from drift_sdk.models._parse import (
    PatternInstance as PatternInstance,
)
from drift_sdk.models._patch import (
    AcceptanceResult as AcceptanceResult,
)
from drift_sdk.models._patch import (
    BlastRadius as BlastRadius,
)
from drift_sdk.models._patch import (
    DiffMetrics as DiffMetrics,
)
from drift_sdk.models._patch import (
    PatchIntent as PatchIntent,
)
from drift_sdk.models._patch import (
    PatchStatus as PatchStatus,
)
from drift_sdk.models._patch import (
    PatchVerdict as PatchVerdict,
)
from drift_sdk.models._policy import (
    CompiledPolicy as CompiledPolicy,
)
from drift_sdk.models._policy import (
    PolicyRule as PolicyRule,
)

__all__ = [
    # Enums & constants
    "OUTPUT_SCHEMA_VERSION",
    "AgentActionType",
    "Severity",
    "FindingStatus",
    "TrendDirection",
    "AnalysisStatus",
    "SignalType",
    "RegressionReasonCode",
    "RegressionPattern",
    "RepairLevel",
    "PatternCategory",
    "NegativeContextCategory",
    "NegativeContextScope",
    "TaskComplexity",
    "AutomationFit",
    "ReviewRisk",
    "ChangeScope",
    "VerificationStrength",
    "RepairMaturity",
    "severity_for_score",
    # Parse / ingestion
    "FileInfo",
    "FunctionInfo",
    "ClassInfo",
    "ImportInfo",
    "PatternInstance",
    "ParseResult",
    # Git
    "CommitInfo",
    "FileHistory",
    "BlameLine",
    "Attribution",
    # Findings & analysis
    "LogicalLocation",
    "Finding",
    "AnalyzerWarning",
    "ModuleScore",
    "TrendContext",
    "RepoAnalysis",
    "AgentAction",
    "AgentTelemetry",
    # Agent
    "AgentTask",
    "ConsolidationGroup",
    "NegativeContext",
    # Patch engine (ADR-074)
    "PatchStatus",
    "BlastRadius",
    "DiffMetrics",
    "PatchIntent",
    "PatchVerdict",
    "AcceptanceResult",
    # Policy
    "CompiledPolicy",
    "PolicyRule",
]
