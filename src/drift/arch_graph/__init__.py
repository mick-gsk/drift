# ruff: noqa: F401, F403, E501
import importlib as _importlib
import sys as _sys

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_engine.arch_graph import AbstractionIndex as AbstractionIndex
from drift_engine.arch_graph import ArchAbstraction as ArchAbstraction
from drift_engine.arch_graph import ArchDecision as ArchDecision
from drift_engine.arch_graph import ArchDependency as ArchDependency
from drift_engine.arch_graph import ArchGraph as ArchGraph
from drift_engine.arch_graph import ArchGraphStore as ArchGraphStore
from drift_engine.arch_graph import ArchHotspot as ArchHotspot
from drift_engine.arch_graph import ArchModule as ArchModule
from drift_engine.arch_graph import PatternProposal as PatternProposal
from drift_engine.arch_graph import ReuseSuggestion as ReuseSuggestion
from drift_engine.arch_graph import SkillBriefing as SkillBriefing
from drift_engine.arch_graph import seed_graph as seed_graph
from drift_engine.arch_graph import suggest_reuse as suggest_reuse

_target = _importlib.import_module("drift_engine.arch_graph")
_sys.modules[__name__] = _target
for _k, _v in list(_sys.modules.items()):
    if _k.startswith("drift_engine.arch_graph."):
        _sys.modules.setdefault(__name__ + _k[23:], _v)
