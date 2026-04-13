"""Negative context model (anti-pattern feed for coding agents)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from drift.models._enums import NegativeContextCategory, NegativeContextScope, Severity


@dataclass
class NegativeContext:
    """An anti-pattern warning derived from drift findings.

    Agents consume these items as "what NOT to do" context before generating
    code.  Each item is deterministically derived from signal findings —
    no LLM involved.
    """

    anti_pattern_id: str
    category: NegativeContextCategory
    source_signal: str
    severity: Severity
    scope: NegativeContextScope
    description: str
    forbidden_pattern: str  # concrete code anti-example
    canonical_alternative: str  # what to do instead
    affected_files: list[str] = field(default_factory=list)
    confidence: float = 1.0
    rationale: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
