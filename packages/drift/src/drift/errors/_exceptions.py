"""Exception hierarchy and YAML context helpers."""

from __future__ import annotations

from typing import Any

from drift.errors._codes import (
    ERROR_REGISTRY,
    EXIT_ANALYSIS_ERROR,
    EXIT_CONFIG_ERROR,
    EXIT_SYSTEM_ERROR,
)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class DriftError(Exception):
    """Base exception for all structured Drift errors."""

    exit_code: int = 2  # default

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        context: str | None = None,
        suggested_action: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.code = code
        self._kwargs = kwargs
        self._context = context
        self.suggested_action = suggested_action

        info = ERROR_REGISTRY.get(code)
        if info and not message:
            self._formatted = info.format(**kwargs)
        elif message:
            self._formatted = f"[{code}] {message}"
        else:
            self._formatted = f"[{code}] Unknown error"

        super().__init__(self._formatted)

    @property
    def hint(self) -> str | None:
        """Return an explain hint for this error code."""
        if self.code in ERROR_REGISTRY:
            return f"Run 'drift explain {self.code}' for details."
        return None

    @property
    def detail(self) -> str:
        """Full formatted message including optional YAML/code context."""
        parts = [self._formatted]
        if self._context:
            parts.append("")
            parts.append(self._context)
        if self.hint:
            parts.append("")
            parts.append(self.hint)
        return "\n".join(parts)


class DriftConfigError(DriftError):
    """User-caused configuration error.  Exit code 2."""

    exit_code = EXIT_CONFIG_ERROR


class DriftSystemError(DriftError):
    """System/environment error.  Exit code 4."""

    exit_code = EXIT_SYSTEM_ERROR


class DriftAnalysisError(DriftError):
    """Analysis pipeline error.  Exit code 3."""

    exit_code = EXIT_ANALYSIS_ERROR


# ---------------------------------------------------------------------------
# YAML context helper
# ---------------------------------------------------------------------------


def yaml_context_snippet(raw_yaml: str, target_line: int, context: int = 2) -> str:
    """Return a few lines of YAML surrounding *target_line* (1-indexed).

    Format matches rustc-style diagnostics::

        10 │ weights:
        11 │   avs: 0.16
      → 12 │   pfs: "not_a_number"
        13 │   mds: 0.13
    """
    lines = raw_yaml.splitlines()
    first = max(0, target_line - 1 - context)
    last = min(len(lines), target_line + context)
    gutter_w = len(str(last))

    out: list[str] = []
    for idx in range(first, last):
        lineno = idx + 1
        marker = "→" if lineno == target_line else " "
        out.append(f"  {marker} {lineno:>{gutter_w}} │ {lines[idx]}")
    return "\n".join(out)


def _find_yaml_line(raw_yaml: str, field_path: tuple[str | int, ...]) -> int | None:
    """Best-effort: find the 1-indexed line of a dotted field path in raw YAML.

    Walks the path segments in order and looks for the key in the text.
    Returns *None* if it cannot be located.
    """
    lines = raw_yaml.splitlines()
    # Walk from the top, matching each segment
    start = 0
    for segment in field_path:
        if isinstance(segment, int):
            continue  # list indices — skip, stay at current block
        key = str(segment)
        for i in range(start, len(lines)):
            stripped = lines[i].lstrip()
            if stripped.startswith(f"{key}:") or stripped.startswith(f"{key} :"):
                start = i + 1
                target = i + 1  # 1-indexed
                break
        else:
            return None
    return target  # type: ignore[possibly-undefined]  # noqa: F821
