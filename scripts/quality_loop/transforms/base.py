"""Base class for all AST-based quality transforms (via libcst)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    import libcst as cst
except ImportError as exc:
    raise ImportError(
        "libcst is required for quality_loop transforms. "
        "Install with: pip install 'drift-analyzer[autopatch]'"
    ) from exc


RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ApplyResult:
    changed: bool
    error: str | None = None


class BaseTransform(cst.CSTTransformer):
    """Abstract base for all quality transforms.

    Subclasses must set class-level attributes:
      name        — unique identifier (snake_case)
      description — one-line description
      risk_level  — 'low' | 'medium' | 'high'
    """

    name: str = ""
    description: str = ""
    risk_level: RiskLevel = "low"

    @classmethod
    def applicable_to(cls, src: str) -> bool:
        """Return True if this transform could apply to the given source.

        Default implementation always returns True.
        Subclasses should override for fast pre-filtering.
        """
        return True


def apply_transform(transform_cls: type[BaseTransform], file: Path) -> ApplyResult:
    """Apply a transform to a file in-place.

    Returns ApplyResult(changed=True) if the file was modified,
    ApplyResult(changed=False) if no change was needed, or
    ApplyResult(changed=False, error=...) if an error occurred.
    Always uses UTF-8 encoding for read/write.
    """
    try:
        source = file.read_text(encoding="utf-8")
    except OSError as exc:
        return ApplyResult(changed=False, error=f"read error: {exc}")

    if not transform_cls.applicable_to(source):
        return ApplyResult(changed=False)

    try:
        tree = cst.parse_module(source)
        new_tree = tree.visit(transform_cls())
        new_source = new_tree.code
    except Exception as exc:  # noqa: BLE001
        return ApplyResult(changed=False, error=f"parse/transform error: {exc}")

    if new_source == source:
        return ApplyResult(changed=False)

    try:
        file.write_text(new_source, encoding="utf-8")
    except OSError as exc:
        return ApplyResult(changed=False, error=f"write error: {exc}")

    return ApplyResult(changed=True)
