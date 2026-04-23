"""Core engine for the Drift Self-Improvement Loop (DSOL, ADR-097)."""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_REPO = Path(".")
DEFAULT_SELF_REPORT = Path("benchmark_results/drift_self.json")
DEFAULT_KPI_TREND = Path("benchmark_results/kpi_trend.jsonl")
DEFAULT_LEDGER = Path(".drift/self_improvement_ledger.jsonl")
DEFAULT_ARTIFACTS_DIR = Path("work_artifacts/self_improvement")

# Priority budget: the loop proposes at most N items per cycle so the
# maintainer inbox cannot explode even if drift_self contains hundreds
# of findings.
DEFAULT_MAX_PROPOSALS = 10


class ImprovementProposal(BaseModel):
    """A single, human-reviewable optimization proposal.

    Proposals are **never** executable patches. They describe the
    observed condition, the rationale (trend slope, repeated
    occurrence, severity) and point to the drift finding(s) a
    maintainer should act on.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    proposal_id: str
    kind: str  # "regressive_signal" | "hotspot_finding" | "stale_audit"
    signal_type: str | None = None
    file_path: str | None = None
    severity: str | None = None
    score: float
    rationale: str
    suggested_action: str
    finding_ids: tuple[str, ...] = Field(default_factory=tuple)
    # Number of consecutive cycles this proposal has been emitted
    # without a maintainer closing it. Compounds priority.
    recurrence: int = 1


class ImprovementReport(BaseModel):
    """Artifact written per cycle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cycle_ts: str
    corpus_sha: str | None = None
    kpi_snapshot: dict[str, float] = Field(default_factory=dict)
    proposals: tuple[ImprovementProposal, ...] = Field(default_factory=tuple)
    observations: tuple[str, ...] = Field(default_factory=tuple)
    ledger_path: str | None = None


class CycleLedgerEntry(BaseModel):
    """Append-only ledger row recording a cycle's top proposals."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cycle_ts: str
    proposal_ids: tuple[str, ...]


# ---------------------------------------------------------------------------
# Load helpers — graceful fallbacks for missing inputs
# ---------------------------------------------------------------------------


def _safe_load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _safe_load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


# ---------------------------------------------------------------------------
# Proposal generation — deterministic and bounded
# ---------------------------------------------------------------------------


def _regressive_signal_proposal(
    kpi_rows: list[dict[str, Any]], window: int
) -> ImprovementProposal | None:
    """Detect the single worst-trending aggregate metric over N snapshots."""
    if len(kpi_rows) < 2:
        return None

    tail = kpi_rows[-window:] if window > 0 else kpi_rows
    if len(tail) < 2:
        return None

    metric_keys = ("aggregate_f1", "mutation_recall", "precision_recall_mean")
    worst_key: str | None = None
    worst_slope = 0.0

    for key in metric_keys:
        values = [r.get(key) for r in tail if isinstance(r.get(key), (int, float))]
        if len(values) < 2:
            continue
        slope = (values[-1] - values[0]) / max(1, len(values) - 1)
        if slope < worst_slope:
            worst_slope = slope
            worst_key = key

    if worst_key is None or worst_slope >= -0.005:
        return None

    return ImprovementProposal(
        proposal_id=f"regressive::{worst_key}",
        kind="regressive_signal",
        signal_type=None,
        score=abs(worst_slope) * 100.0,
        rationale=(
            f"KPI '{worst_key}' degrades with slope {worst_slope:+.4f} across "
            f"the last {len(tail)} snapshots. Trend gate may block the next "
            f"release unless the root cause is reviewed."
        ),
        suggested_action=(
            f"Open an investigation ADR for '{worst_key}'. Inspect per-signal "
            f"precision/recall in benchmark_results/ and identify the signal "
            f"(or fixture) responsible for the drift."
        ),
    )


def _hotspot_proposals(
    self_report: dict[str, Any],
    previous_ids: set[str],
    max_items: int,
) -> list[ImprovementProposal]:
    """Pick the top-N highest-impact findings from the self-scan."""
    findings = self_report.get("findings") or []
    if not isinstance(findings, list):
        return []

    # Severity -> numeric for deterministic ranking.
    sev_weight = {"critical": 4.0, "high": 3.0, "medium": 2.0, "low": 1.0}
    ranked: list[tuple[float, dict[str, Any]]] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        sev = str(f.get("severity", "low")).lower()
        score = float(f.get("score", 0.0) or 0.0)
        impact = sev_weight.get(sev, 1.0) * (0.5 + score)
        ranked.append((impact, f))

    ranked.sort(key=lambda t: (-t[0], str(t[1].get("id", ""))))
    proposals: list[ImprovementProposal] = []
    signal_counter: Counter[str] = Counter()

    for impact, f in ranked:
        sig = str(f.get("signal_type") or f.get("rule_id") or "unknown")
        # Cap per-signal dominance — never let one signal swamp the cycle.
        if signal_counter[sig] >= max(1, max_items // 3):
            continue
        signal_counter[sig] += 1

        fid = str(f.get("id") or f.get("finding_id") or f"{sig}:{f.get('file_path')}")
        proposal_id = f"hotspot::{fid}"
        recurrence = 2 if proposal_id in previous_ids else 1
        proposals.append(
            ImprovementProposal(
                proposal_id=proposal_id,
                kind="hotspot_finding",
                signal_type=sig,
                file_path=str(f.get("file_path")) if f.get("file_path") else None,
                severity=str(f.get("severity")).lower() if f.get("severity") else None,
                score=round(impact, 3),
                rationale=(
                    f"High-impact finding in signal '{sig}' at "
                    f"{f.get('file_path')}:{f.get('start_line')}. "
                    f"Impact={impact:.2f} (severity × score). "
                    f"{'Recurring from previous cycle.' if recurrence > 1 else ''}"
                ).strip(),
                suggested_action=(
                    f"Review {f.get('file_path')}: {f.get('title') or ''}. "
                    f"Apply fix or open an ADR justifying suppression."
                ).strip(),
                finding_ids=(fid,),
                recurrence=recurrence,
            )
        )
        if len(proposals) >= max_items:
            break

    return proposals


def _stale_audit_proposal(repo: Path) -> ImprovementProposal | None:
    """Flag audit artefacts that are older than 90 days when signals changed.

    Pure filesystem check: no git blame, no network. If the signals
    package has changed more recently than any of the audit artefacts,
    emit a proposal.
    """
    audit_dir = repo / "audit_results"
    signals_dir = repo / "src" / "drift" / "signals"
    if not audit_dir.is_dir() or not signals_dir.is_dir():
        return None

    def _latest_mtime(root: Path) -> float:
        best = 0.0
        for p in root.rglob("*.py" if root.name == "signals" else "*.md"):
            try:
                m = p.stat().st_mtime
            except OSError:
                continue
            if m > best:
                best = m
        return best

    signals_m = _latest_mtime(signals_dir)
    audit_m = _latest_mtime(audit_dir)
    if signals_m == 0.0 or audit_m == 0.0:
        return None

    gap_days = (signals_m - audit_m) / 86400.0
    if gap_days < 14:
        return None

    return ImprovementProposal(
        proposal_id="stale_audit::signals",
        kind="stale_audit",
        score=round(gap_days, 2),
        rationale=(
            f"Signals package changed {gap_days:.1f} days after the most "
            f"recent audit artefact. Policy §18 requires audit refresh "
            f"when signal/ingestion/output code changes."
        ),
        suggested_action=(
            "Run `make audit-diff` and update audit_results/{fmea_matrix,"
            "risk_register,stride_threat_model,fault_trees}.md as required."
        ),
    )


# ---------------------------------------------------------------------------
# Cycle orchestration
# ---------------------------------------------------------------------------


class SelfImprovementEngine:
    """Runs one DSOL cycle and writes its artefacts."""

    def __init__(
        self,
        repo: Path = DEFAULT_REPO,
        *,
        self_report: Path | None = None,
        kpi_trend: Path | None = None,
        ledger: Path | None = None,
        artifacts_dir: Path | None = None,
        max_proposals: int = DEFAULT_MAX_PROPOSALS,
        trend_window: int = 5,
    ) -> None:
        self.repo = Path(repo)
        self.self_report = self.repo / (self_report or DEFAULT_SELF_REPORT)
        self.kpi_trend = self.repo / (kpi_trend or DEFAULT_KPI_TREND)
        self.ledger = self.repo / (ledger or DEFAULT_LEDGER)
        self.artifacts_dir = self.repo / (artifacts_dir or DEFAULT_ARTIFACTS_DIR)
        self.max_proposals = max_proposals
        self.trend_window = trend_window

    # -----------------------------------------------------------------

    def _load_previous_ids(self) -> set[str]:
        ids: set[str] = set()
        for row in _safe_load_jsonl(self.ledger):
            for pid in row.get("proposal_ids") or ():
                if isinstance(pid, str):
                    ids.add(pid)
        return ids

    def _kpi_snapshot(self, rows: list[dict[str, Any]]) -> dict[str, float]:
        if not rows:
            return {}
        latest = rows[-1]
        out: dict[str, float] = {}
        for k, v in latest.items():
            if isinstance(v, (int, float)):
                out[k] = float(v)
        return out

    def run(self) -> ImprovementReport:
        observations: list[str] = []
        self_raw = _safe_load_json(self.self_report)
        self_report_obj: dict[str, Any] = (
            self_raw if isinstance(self_raw, dict) else {}
        )
        if not self_report_obj:
            observations.append(
                f"self-scan report missing at {self.self_report} — hotspot "
                "proposals skipped"
            )

        kpi_rows = _safe_load_jsonl(self.kpi_trend)
        if not kpi_rows:
            observations.append(
                f"kpi trend log missing at {self.kpi_trend} — regressive-signal "
                "detection skipped"
            )

        previous_ids = self._load_previous_ids()
        proposals: list[ImprovementProposal] = []

        regressive = _regressive_signal_proposal(kpi_rows, self.trend_window)
        if regressive is not None:
            proposals.append(regressive)

        if self_report_obj:
            proposals.extend(
                _hotspot_proposals(
                    self_report_obj,
                    previous_ids,
                    max_items=max(0, self.max_proposals - len(proposals)),
                )
            )

        stale = _stale_audit_proposal(self.repo)
        if stale is not None:
            proposals.append(stale)

        # Final deterministic sort: recurrence desc, then score desc, then id.
        proposals.sort(key=lambda p: (-p.recurrence, -p.score, p.proposal_id))
        if len(proposals) > self.max_proposals:
            proposals = proposals[: self.max_proposals]

        cycle_ts = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")

        report = ImprovementReport(
            cycle_ts=cycle_ts,
            corpus_sha=str(self_report_obj.get("schema_version") or "") or None,
            kpi_snapshot=self._kpi_snapshot(kpi_rows),
            proposals=tuple(proposals),
            observations=tuple(observations),
            ledger_path=str(self.ledger.relative_to(self.repo))
            if self.ledger.is_relative_to(self.repo)
            else str(self.ledger),
        )

        self._write_artifacts(report)
        self._append_ledger(report)
        return report

    # -----------------------------------------------------------------

    def _write_artifacts(self, report: ImprovementReport) -> None:
        cycle_dir = self.artifacts_dir / report.cycle_ts
        cycle_dir.mkdir(parents=True, exist_ok=True)

        (cycle_dir / "proposals.json").write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

        lines = [
            f"# Self-Improvement Cycle {report.cycle_ts}",
            "",
            f"- Proposals: **{len(report.proposals)}**",
            f"- KPI snapshot keys: {sorted(report.kpi_snapshot)}",
            "",
        ]
        if report.observations:
            lines.append("## Observations")
            for obs in report.observations:
                lines.append(f"- {obs}")
            lines.append("")
        lines.append("## Proposals")
        if not report.proposals:
            lines.append("- _none_")
        for p in report.proposals:
            lines.append(f"### [{p.kind}] {p.proposal_id}")
            lines.append(f"- score: {p.score}")
            lines.append(f"- recurrence: {p.recurrence}")
            if p.signal_type:
                lines.append(f"- signal: `{p.signal_type}`")
            if p.file_path:
                lines.append(f"- file: `{p.file_path}`")
            if p.severity:
                lines.append(f"- severity: `{p.severity}`")
            lines.append(f"- rationale: {p.rationale}")
            lines.append(f"- suggested action: {p.suggested_action}")
            lines.append("")
        (cycle_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    def _append_ledger(self, report: ImprovementReport) -> None:
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        entry = CycleLedgerEntry(
            cycle_ts=report.cycle_ts,
            proposal_ids=tuple(p.proposal_id for p in report.proposals),
        )
        with self.ledger.open("a", encoding="utf-8") as fh:
            fh.write(entry.model_dump_json() + "\n")


def run_cycle(repo: Path = DEFAULT_REPO, **kwargs: Any) -> ImprovementReport:
    """Module-level convenience wrapper used by the CLI and cron entry points."""
    return SelfImprovementEngine(repo=repo, **kwargs).run()
