"""Agent task model (agent-tasks output format)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from drift.models._context import NegativeContext
from drift.models._enums import RegressionPattern, Severity


@dataclass
class AgentTask:
    """An atomic, machine-readable repair task derived from a Finding."""

    id: str
    signal_type: str  # SignalType value for core signals, arbitrary str for plugins
    severity: Severity
    priority: int
    title: str
    description: str
    action: str
    file_path: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    related_files: list[str] = field(default_factory=list)
    complexity: str = "medium"
    expected_effect: str = ""
    success_criteria: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # Phase 1: Automation fitness classification
    automation_fit: str = "medium"  # "high" | "medium" | "low"
    review_risk: str = "medium"  # "low" | "medium" | "high"
    change_scope: str = "local"  # "local" | "module" | "cross-module"
    verification_strength: str = "moderate"  # "strong" | "moderate" | "weak"
    # Phase 2: Do-not-over-fix guardrails
    constraints: list[str] = field(default_factory=list)
    # Phase 4: Signal-specific repair maturity
    repair_maturity: str = "experimental"  # "verified" | "experimental" | "indirect-only"
    # Negative context: anti-patterns the agent must NOT reproduce
    negative_context: list[NegativeContext] = field(default_factory=list)
    # Expected score reduction when this task is resolved
    expected_score_delta: float = 0.0
    # ADR-025 Phase A: Task-graph fields for orchestration
    blocks: list[str] = field(default_factory=list)  # inverse of depends_on
    batch_group: str | None = None  # cluster ID for co-fixable tasks
    preferred_order: int = 0  # topological sort index within session
    parallel_with: list[str] = field(default_factory=list)  # task IDs safe to run concurrently
    # Signal-specific, ordered verification steps (machine-executable)
    verify_plan: list[dict[str, Any]] = field(default_factory=list)
    # ADR-064: shadow-verify for cross-file-risky edit_kinds
    shadow_verify: bool = False  # True when drift_nudge is insufficient for verification
    shadow_verify_scope: list[str] = field(default_factory=list)  # files to re-scan
    # Repair template registry fields (ADR-065)
    # None = insufficient outcome data in the registry (<3 entries)
    template_confidence: float | None = None
    regression_guidance: list[RegressionPattern] = field(default_factory=list)
