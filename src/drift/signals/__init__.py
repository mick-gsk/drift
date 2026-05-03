"""Detection signals for Drift analysis."""

from drift_engine.signals.architecture_violation import ArchitectureViolationSignal
from drift_engine.signals.base import BaseSignal
from drift_engine.signals.broad_exception_monoculture import BroadExceptionMonocultureSignal
from drift_engine.signals.bypass_accumulation import BypassAccumulationSignal
from drift_engine.signals.circular_import import CircularImportSignal
from drift_engine.signals.co_change_coupling import CoChangeCouplingSignal
from drift_engine.signals.cognitive_complexity import CognitiveComplexitySignal
from drift_engine.signals.cohesion_deficit import CohesionDeficitSignal
from drift_engine.signals.dead_code_accumulation import DeadCodeAccumulationSignal
from drift_engine.signals.doc_impl_drift import DocImplDriftSignal
from drift_engine.signals.exception_contract_drift import ExceptionContractDriftSignal
from drift_engine.signals.explainability_deficit import ExplainabilityDeficitSignal
from drift_engine.signals.fan_out_explosion import FanOutExplosionSignal
from drift_engine.signals.guard_clause_deficit import GuardClauseDeficitSignal
from drift_engine.signals.mutant_duplicates import MutantDuplicateSignal
from drift_engine.signals.naming_contract_violation import NamingContractViolationSignal
from drift_engine.signals.pattern_fragmentation import PatternFragmentationSignal
from drift_engine.signals.phantom_reference import PhantomReferenceSignal
from drift_engine.signals.system_misalignment import SystemMisalignmentSignal
from drift_engine.signals.temporal_volatility import TemporalVolatilitySignal
from drift_engine.signals.test_polarity_deficit import TestPolarityDeficitSignal
from drift_engine.signals.ts_architecture import TypeScriptArchitectureSignal

__all__ = [
    "BaseSignal",
    "PatternFragmentationSignal",
    "ArchitectureViolationSignal",
    "MutantDuplicateSignal",
    "ExplainabilityDeficitSignal",
    "TemporalVolatilitySignal",
    "SystemMisalignmentSignal",
    "DocImplDriftSignal",
    "BroadExceptionMonocultureSignal",
    "TestPolarityDeficitSignal",
    "GuardClauseDeficitSignal",
    "CoChangeCouplingSignal",
    "CohesionDeficitSignal",
    "NamingContractViolationSignal",
    "BypassAccumulationSignal",
    "ExceptionContractDriftSignal",
    "TypeScriptArchitectureSignal",
    "CognitiveComplexitySignal",
    "FanOutExplosionSignal",
    "CircularImportSignal",
    "DeadCodeAccumulationSignal",
    "PhantomReferenceSignal",
]
