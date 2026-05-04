"""Build and persist SessionData from a RepoAnalysis."""
from __future__ import annotations

from pathlib import Path

from drift_engine.baseline import finding_fingerprint
from drift_sdk.models._enums import Severity
from drift_sdk.models._findings import RepoAnalysis

from ._models import SessionData, TopFinding

_SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


def build_session_data(analysis: RepoAnalysis) -> SessionData:
    """Build a :class:`SessionData` from a completed :class:`RepoAnalysis`."""
    sorted_findings = sorted(
        analysis.findings,
        key=lambda f: (_SEVERITY_RANK.get(f.severity.value, 99), -f.impact),
    )
    top_findings: list[TopFinding] = [
        TopFinding(
            signal_type=f.signal_type,
            severity=f.severity.value,
            file_path=f.file_path.as_posix() if f.file_path else "",
            line_range=(
                (f.start_line, f.end_line)
                if f.start_line is not None and f.end_line is not None
                else None
            ),
            reason=f.human_message or f.description or f.title,
            finding_id=finding_fingerprint(f),
        )
        for f in sorted_findings[:5]
    ]
    grade_letter, grade_label = analysis.grade
    return SessionData(
        schema_version="1.0",
        repo_path=analysis.repo_path.as_posix(),
        analyzed_at=analysis.analyzed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        drift_score=round(max(0.0, min(1.0, analysis.drift_score)), 3),
        grade=grade_letter,
        grade_label=grade_label,
        top_findings=top_findings,
        findings_total=len(analysis.findings),
        critical_count=sum(1 for f in analysis.findings if f.severity == Severity.CRITICAL),
        high_count=sum(1 for f in analysis.findings if f.severity == Severity.HIGH),
    )


def write_session_file(repo: Path, data: SessionData) -> Path | None:
    """Write *data* to ``<repo>/.vscode/drift-session.json``.

    Returns the written :class:`~pathlib.Path`, or ``None`` when the
    ``.vscode/`` directory does not exist (skips silently).
    """
    vscode_dir = repo / ".vscode"
    if not vscode_dir.exists():
        return None
    session_path = vscode_dir / "drift-session.json"
    session_path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
    return session_path
