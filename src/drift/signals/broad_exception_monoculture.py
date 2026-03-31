"""Signal 8: Broad Exception Monoculture (BEM).

Detects modules where exception handling is uniformly broad —
catching ``Exception``, ``BaseException`` or bare ``except`` — and
uniformly swallowing (pass / log / print without re-raise).

This is a proxy for *consistent wrongness* (EPISTEMICS §2): when every
handler looks the same and catches everything, real error classes are
silently discarded.  The signal does NOT judge *what* is caught, only
that the handling is uniform-broad across an entire module.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path, PurePosixPath

from drift.config import DriftConfig
from drift.models import (
    FileHistory,
    Finding,
    ParseResult,
    PatternCategory,
    Severity,
    SignalType,
)
from drift.signals.base import BaseSignal, register_signal

_BROAD_TYPES: frozenset[str] = frozenset({
    "bare", "Exception", "BaseException",
    "any", "unknown", "Error",
})

_SWALLOWING_ACTIONS: frozenset[str] = frozenset({"pass", "log", "print"})

# Module-name stems that legitimately use broad exception handling
# (error boundaries, middleware).  Findings here are excluded.
_BOUNDARY_STEMS: frozenset[str] = frozenset({
    "middleware",
    "error_handler",
    "exception_handler",
    "error_boundary",
    "error_middleware",
    "celery_error",
    "task_error",
    "signal_handler",
    "fallback",
    "recovery",
})

# Decorators that indicate intentional error-boundary design.
_BOUNDARY_DECORATORS: frozenset[str] = frozenset({
    "app.exception_handler",
    "app.errorhandler",
    "app_errorhandler",
    "errorhandler",
    "exception_handler",
    "error_handler",
    "receiver",
    "task",
    "shared_task",
})


def _is_error_boundary(file_path: Path) -> bool:
    """Return True if a file is an intentional error-boundary module."""
    stem = file_path.stem.lower()
    return any(b in stem for b in _BOUNDARY_STEMS)


def _has_boundary_decorator(parse_result: ParseResult) -> bool:
    """Return True if any function in the file uses a boundary decorator."""
    for fn in parse_result.functions:
        for dec in fn.decorators:
            dec_lower = dec.lower()
            if any(bd in dec_lower for bd in _BOUNDARY_DECORATORS):
                return True
    return False


@register_signal
class BroadExceptionMonocultureSignal(BaseSignal):
    """Detect modules with uniformly broad exception handling."""

    incremental_scope = "file_local"

    @property
    def signal_type(self) -> SignalType:
        return SignalType.BROAD_EXCEPTION_MONOCULTURE

    @property
    def name(self) -> str:
        return "Broad Exception Monoculture"

    def analyze(
        self,
        parse_results: list[ParseResult],
        file_histories: dict[str, FileHistory],
        config: DriftConfig,
    ) -> list[Finding]:
        """Flag modules where most exception handlers catch only broad types.

        A module is flagged when >=bem_min_handlers handlers exist and
        the broad-handler ratio exceeds 0.7.  Error-boundary modules
        (e.g. middleware, error_handler) are excluded.
        """
        min_handlers = config.thresholds.bem_min_handlers

        # Group error-handling patterns by module directory
        module_handlers: dict[str, list[tuple[Path, dict]]] = defaultdict(list)
        # Track parse results per module for decorator analysis
        module_parse_results: dict[str, list[ParseResult]] = defaultdict(list)

        for pr in parse_results:
            module_key = PurePosixPath(pr.file_path.parent).as_posix()
            module_parse_results[module_key].append(pr)
            for pat in pr.patterns:
                if pat.category != PatternCategory.ERROR_HANDLING:
                    continue
                handlers = pat.fingerprint.get("handlers", [])
                if not handlers:
                    continue
                for h in handlers:
                    module_handlers[module_key].append((pr.file_path, h))

        findings: list[Finding] = []

        for module_key, handler_list in module_handlers.items():
            if len(handler_list) < min_handlers:
                continue

            # Skip error-boundary modules (by filename or decorator)
            files_in_module = {fp for fp, _ in handler_list}
            if all(_is_error_boundary(fp) for fp in files_in_module):
                continue
            prs_in_module = [
                pr
                for pr in module_parse_results.get(module_key, [])
                if pr.file_path in files_in_module
            ]
            if prs_in_module and all(_has_boundary_decorator(pr) for pr in prs_in_module):
                continue

            broad_count = 0
            swallowing_count = 0
            total = len(handler_list)

            for _, h in handler_list:
                exc_type = h.get("exception_type", "")
                actions = set(h.get("actions", []))

                if exc_type in _BROAD_TYPES:
                    broad_count += 1

                if actions and actions <= _SWALLOWING_ACTIONS:
                    swallowing_count += 1

            broadness = broad_count / total
            swallowing = swallowing_count / total

            if broadness < 0.80 or swallowing < 0.60:
                continue

            score = round(min(1.0, broadness * swallowing), 3)

            severity = Severity.HIGH if score >= 0.7 else Severity.MEDIUM

            related = sorted(files_in_module, key=lambda fp: fp.as_posix())

            findings.append(
                Finding(
                    signal_type=self.signal_type,
                    severity=severity,
                    score=score,
                    title=f"Broad exception monoculture in {module_key}/",
                    description=(
                        f"{broad_count}/{total} handlers catch broad exceptions "
                        f"({broadness:.0%}), {swallowing_count}/{total} swallow "
                        f"errors ({swallowing:.0%})."
                    ),
                    file_path=Path(module_key),
                    related_files=related,
                    fix=(
                        "Differentiate exception handlers: catch specific "
                        "exception types and re-raise or convert unknown errors."
                    ),
                    metadata={
                        "total_handlers": total,
                        "broad_count": broad_count,
                        "swallowing_count": swallowing_count,
                        "broadness_ratio": broadness,
                        "swallowing_ratio": swallowing,
                    },
                )
            )

        return findings
