"""Base interface for detection signals."""

from __future__ import annotations

import fnmatch
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Literal, Protocol, cast, runtime_checkable

from drift.config import DriftConfig
from drift.models import AnalyzerWarning, CommitInfo, FileHistory, Finding, ParseResult, SignalType

if TYPE_CHECKING:
    import numpy as np


@runtime_checkable
class EmbeddingServiceProtocol(Protocol):
    """Minimal interface expected by signal infrastructure for embeddings."""

    def embed_text(self, text: str) -> np.ndarray | None: ...

    def embed_texts(self, texts: list[str]) -> list[np.ndarray | None]: ...

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float: ...

    @staticmethod
    def build_index(vectors: list[np.ndarray] | np.ndarray) -> object | None: ...

    @staticmethod
    def search_index(
        index: object,
        query: np.ndarray,
        top_k: int = 10,
    ) -> list[tuple[int, float]]: ...


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
    embedding_service: EmbeddingServiceProtocol | None = None
    commits: list[CommitInfo] = field(default_factory=list)


@dataclass(slots=True)
class SignalCapabilities:
    """Explicit runtime capabilities provided by the analyzer to each signal."""

    repo_path: Path
    embedding_service: EmbeddingServiceProtocol | None
    commits: list[CommitInfo]

    @classmethod
    def from_analysis_context(cls, ctx: AnalysisContext) -> SignalCapabilities:
        """Build a capabilities payload from the full analysis context."""
        return cls(
            repo_path=ctx.repo_path,
            embedding_service=ctx.embedding_service,
            commits=ctx.commits,
        )


@dataclass(frozen=True, slots=True)
class SignalCacheDependencySpec:
    """Declarative cache-dependency contract for signal result invalidation."""

    scope: Literal["file_local", "module_wide", "repo_wide", "git_dependent"]
    include_languages: tuple[str, ...] = ()
    include_path_globs: tuple[str, ...] = ()
    exclude_path_globs: tuple[str, ...] = ()


class BaseSignal(ABC):
    """Abstract base class for all detection signals.

    Each signal analyzes a specific dimension of architectural drift
    and produces findings with scores between 0.0 (no drift) and
    1.0 (severe drift).
    """

    incremental_scope: ClassVar[
        Literal["file_local", "cross_file", "git_dependent"]
    ] = "cross_file"
    cache_dependency_scope: ClassVar[
        Literal["file_local", "module_wide", "repo_wide", "git_dependent"]
    ] = "repo_wide"
    cache_dependency_spec: ClassVar[SignalCacheDependencySpec | None] = None
    uses_embeddings: ClassVar[bool] = False
    depends_on_signals: ClassVar[tuple[str, ...]] = ()

    _repo_path: Path | None
    _embedding_service: EmbeddingServiceProtocol | None
    _commits: list[CommitInfo]

    def __init__(
        self,
        *,
        repo_path: Path | None = None,
        embedding_service: EmbeddingServiceProtocol | None = None,
        commits: list[CommitInfo] | None = None,
    ) -> None:
        self._repo_path = repo_path
        self._embedding_service = embedding_service
        self._commits = commits if commits is not None else []
        self._warnings: list[AnalyzerWarning] = []

    def emit_warning(self, message: str, *, skipped: bool = True) -> None:
        """Record a non-finding diagnostic for this signal."""
        self._warnings.append(
            AnalyzerWarning(
                signal_type=str(self.signal_type),
                message=message,
                skipped=skipped,
            )
        )

    def bind_context(self, capabilities: SignalCapabilities) -> None:
        """Bind analyzer-provided runtime capabilities to this signal instance."""
        self._repo_path = capabilities.repo_path
        self._embedding_service = capabilities.embedding_service
        self._commits = capabilities.commits

    @property
    def repo_path(self) -> Path | None:
        """Repository root path if provided by the analyzer."""
        return self._repo_path

    @property
    def embedding_service(self) -> EmbeddingServiceProtocol | None:
        """Embedding service if enabled for the current analysis run."""
        return self._embedding_service

    @property
    def commits(self) -> list[CommitInfo]:
        """Commit history available for co-change style analysis."""
        return self._commits

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

    def should_process_file(self, parse_result: ParseResult) -> bool:
        """Return whether a file-local run should include this parse result.

        Signals can override this to cheaply pre-filter irrelevant files in
        file-local cache mode.
        """
        return True

    def resolve_cache_dependency_spec(self) -> SignalCacheDependencySpec:
        """Return dependency spec with legacy fallback from existing scope fields."""
        explicit_spec = getattr(self, "cache_dependency_spec", None)
        if isinstance(explicit_spec, SignalCacheDependencySpec):
            return explicit_spec

        explicit_scope = getattr(self, "cache_dependency_scope", None)
        if isinstance(explicit_scope, str) and explicit_scope in {
            "file_local",
            "module_wide",
            "repo_wide",
            "git_dependent",
        }:
            return SignalCacheDependencySpec(scope=explicit_scope)

        incremental_scope = getattr(self, "incremental_scope", "cross_file")
        if incremental_scope == "file_local":
            return SignalCacheDependencySpec(scope="file_local")
        if incremental_scope == "git_dependent":
            return SignalCacheDependencySpec(scope="git_dependent")
        return SignalCacheDependencySpec(scope="repo_wide")

    def cache_dependency_paths(self, parse_results: list[ParseResult]) -> set[str] | None:
        """Return selected repo paths for cache invalidation, or ``None`` for all files."""
        spec = self.resolve_cache_dependency_spec()
        if (
            not spec.include_languages
            and not spec.include_path_globs
            and not spec.exclude_path_globs
        ):
            return None

        allowed_languages = {lang.lower() for lang in spec.include_languages}
        selected: set[str] = set()
        for pr in parse_results:
            path_str = pr.file_path.as_posix()
            if allowed_languages and pr.language.lower() not in allowed_languages:
                continue
            if spec.include_path_globs and not any(
                fnmatch.fnmatch(path_str, pattern) for pattern in spec.include_path_globs
            ):
                continue
            if any(fnmatch.fnmatch(path_str, pattern) for pattern in spec.exclude_path_globs):
                continue
            selected.add(path_str)

        return selected


# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------

_SIGNAL_REGISTRY: list[type[BaseSignal]] = []
_SIGNAL_TYPE_VALUE_CACHE: dict[type[BaseSignal], str] = {}


def register_signal(cls: type[BaseSignal]) -> type[BaseSignal]:
    """Class decorator that registers a signal for automatic discovery."""
    _SIGNAL_REGISTRY.append(cls)
    return cls


def _instantiate_signal(
    cls: type[BaseSignal],
    capabilities: SignalCapabilities,
) -> BaseSignal:
    """Instantiate a signal class with explicit contract and legacy fallback."""
    try:
        return cls()
    except TypeError:
        legacy_ctor = cast(Callable[..., BaseSignal], cls)
        try:
            return legacy_ctor(
                repo_path=capabilities.repo_path,
                embedding_service=capabilities.embedding_service,
            )
        except TypeError as legacy_error:
            raise TypeError(
                f"Signal '{cls.__name__}' could not be instantiated. "
                "Expected either a parameterless constructor or the legacy "
                "constructor signature (__init__(repo_path=..., embedding_service=...))."
            ) from legacy_error


def create_signals(
    ctx: AnalysisContext,
    *,
    active_signals: set[str] | None = None,
) -> list[BaseSignal]:
    """Instantiate registered signals with optional pre-filtering.

    Preferred contract:
    1. Parameterless constructor on the signal class
    2. Analyzer calls ``bind_context`` with explicit runtime capabilities

    Backward compatibility:
    Legacy signal constructors accepting ``repo_path`` and
    ``embedding_service`` keywords are still supported.
    """
    capabilities = SignalCapabilities.from_analysis_context(ctx)

    signals: list[BaseSignal] = []
    for cls in _SIGNAL_REGISTRY:
        if active_signals is not None:
            cached_type = _SIGNAL_TYPE_VALUE_CACHE.get(cls)
            if cached_type is None:
                probe = _instantiate_signal(cls, capabilities)
                cached_type = str(probe.signal_type)
                _SIGNAL_TYPE_VALUE_CACHE[cls] = cached_type
                if cached_type not in active_signals:
                    continue
                probe.bind_context(capabilities)
                signals.append(probe)
                continue
            if cached_type not in active_signals:
                continue
        inst = _instantiate_signal(cls, capabilities)
        inst.bind_context(capabilities)
        signals.append(inst)
    return signals


def registered_signals() -> list[type[BaseSignal]]:
    """Return a copy of the current signal registry (for testing)."""
    return list(_SIGNAL_REGISTRY)
