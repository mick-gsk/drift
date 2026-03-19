"""Base interface for detection signals."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from drift.config import DriftConfig
from drift.models import FileHistory, Finding, ParseResult, SignalType

if TYPE_CHECKING:
    from drift.embeddings import EmbeddingService


@dataclass
class AnalysisContext:
    """Shared context passed to all signals during analysis.

    Provides standardised access to repo-level data so that signals
    don't need heterogeneous constructor arguments.
    """

    repo_path: Path
    config: DriftConfig
    parse_results: list[ParseResult] = field(default_factory=list)
    file_histories: dict[str, FileHistory] = field(default_factory=dict)
    embedding_service: EmbeddingService | None = None


class BaseSignal(ABC):
    """Abstract base class for all detection signals.

    Each signal analyzes a specific dimension of architectural drift
    and produces findings with scores between 0.0 (no drift) and
    1.0 (severe drift).
    """

    @property
    @abstractmethod
    def signal_type(self) -> SignalType: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        """Run this signal's detection logic and return findings."""
        ...


# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------

_SIGNAL_REGISTRY: list[type[BaseSignal]] = []


def register_signal(cls: type[BaseSignal]) -> type[BaseSignal]:
    """Class decorator that registers a signal for automatic discovery."""
    _SIGNAL_REGISTRY.append(cls)
    return cls


def create_signals(ctx: AnalysisContext) -> list[BaseSignal]:
    """Instantiate all registered signals.

    Signals whose ``__init__`` accepts a ``repo_path`` keyword argument
    receive it from the context automatically.  All signals receive
    ``ctx.embedding_service`` as a ``_embedding_service`` attribute.
    """
    import inspect

    signals: list[BaseSignal] = []
    for cls in _SIGNAL_REGISTRY:
        sig = inspect.signature(cls.__init__)
        params = set(sig.parameters.keys()) - {"self"}
        inst = cls(repo_path=ctx.repo_path) if "repo_path" in params else cls()
        inst._embedding_service = ctx.embedding_service  # type: ignore[attr-defined]
        signals.append(inst)
    return signals


def registered_signals() -> list[type[BaseSignal]]:
    """Return a copy of the current signal registry (for testing)."""
    return list(_SIGNAL_REGISTRY)
