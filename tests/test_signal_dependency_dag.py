from __future__ import annotations

from drift.models import SignalType
from drift.signals.base import BaseSignal
from drift.signals.dependency_dag import order_signal_classes_topologically


class _ASignal(BaseSignal):
    incremental_scope = "file_local"

    @property
    def signal_type(self) -> SignalType:
        return SignalType.PATTERN_FRAGMENTATION

    @property
    def name(self) -> str:
        return "a"

    def analyze(self, parse_results, file_histories, config):  # type: ignore[override]
        return []


class _BSignal(BaseSignal):
    incremental_scope = "file_local"
    depends_on_signals = (SignalType.PATTERN_FRAGMENTATION.value,)

    @property
    def signal_type(self) -> SignalType:
        return SignalType.COGNITIVE_COMPLEXITY

    @property
    def name(self) -> str:
        return "b"

    def analyze(self, parse_results, file_histories, config):  # type: ignore[override]
        return []


class _CycleSignal(BaseSignal):
    incremental_scope = "file_local"
    depends_on_signals = (SignalType.COGNITIVE_COMPLEXITY.value,)

    @property
    def signal_type(self) -> SignalType:
        return SignalType.PATTERN_FRAGMENTATION

    @property
    def name(self) -> str:
        return "cycle"

    def analyze(self, parse_results, file_histories, config):  # type: ignore[override]
        return []


def test_topological_order_respects_dependencies() -> None:
    ordered = order_signal_classes_topologically([_BSignal, _ASignal])
    assert ordered == [_ASignal, _BSignal]


def test_topological_order_falls_back_on_cycle() -> None:
    ordered = order_signal_classes_topologically([_CycleSignal, _BSignal])
    assert ordered == [_CycleSignal, _BSignal]
