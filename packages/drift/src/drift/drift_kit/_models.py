"""Pydantic models for drift-kit (drift → VS Code Copilot Chat integration)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator

_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}


class TopFinding(BaseModel, frozen=True):
    """Compact summary of a single finding for the drift-kit payload."""

    signal_type: str
    severity: str  # "critical" | "high" | "medium" | "low" | "info"
    file_path: str  # POSIX, repo-relative; "" when no file
    line_range: tuple[int, int] | None
    reason: str
    finding_id: str

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v: str) -> str:
        if v not in _VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_VALID_SEVERITIES)}, got {v!r}")
        return v


class SessionData(BaseModel, frozen=True):
    """Full analysis snapshot written to .vscode/drift-session.json."""

    schema_version: str = "1.0"
    repo_path: str
    analyzed_at: str  # ISO 8601 UTC  YYYY-MM-DDTHH:MM:SSZ
    drift_score: float  # 0.0–1.0, rounded to 3 dp
    grade: str
    grade_label: str
    top_findings: list[TopFinding]
    findings_total: int
    critical_count: int
    high_count: int

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"schema_version must be '1.0', got {v!r}")
        return v

    @field_validator("drift_score")
    @classmethod
    def _validate_drift_score(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"drift_score must be 0.0–1.0, got {v!r}")
        return v


class HandoffBlock(BaseModel, frozen=True):
    """Payload rendered in terminal and injected into JSON output."""

    drift_score: float
    grade: str
    analyzed_at: str
    top_findings: list[TopFinding]
    prompts: list[str]
    session_file: str
    findings_total: int
