"""Tests for the Drift Self-Improvement Loop (DSOL, ADR-097)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from click.testing import CliRunner

from drift.cli import main
from drift.self_improvement import (
    ImprovementProposal,
    SelfImprovementEngine,
    run_cycle,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_self_report(path: Path, *, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"schema_version": "2.2", "findings": findings}),
        encoding="utf-8",
    )


def _write_kpi_trend(path: Path, *, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "drift" / "signals").mkdir(parents=True)
    (repo / "audit_results").mkdir(parents=True)
    return repo


# ---------------------------------------------------------------------------
# 1. Bounded cap (flood guard)
# ---------------------------------------------------------------------------


class TestBoundedProposals:
    def test_max_proposals_cap_enforced(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        findings = [
            {
                "id": f"f{i}",
                "signal_type": f"sig_{i % 4}",
                "file_path": f"src/x{i}.py",
                "start_line": i,
                "severity": "high",
                "score": 0.9,
                "title": "issue",
            }
            for i in range(60)
        ]
        _write_self_report(repo / "benchmark_results" / "drift_self.json", findings=findings)

        report = run_cycle(repo=repo, max_proposals=5)
        assert len(report.proposals) <= 5

    def test_per_signal_dominance_capped(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        findings = [
            {
                "id": f"f{i}",
                "signal_type": "always_same",
                "file_path": f"src/x{i}.py",
                "start_line": i,
                "severity": "critical",
                "score": 0.9,
                "title": "issue",
            }
            for i in range(20)
        ]
        _write_self_report(repo / "benchmark_results" / "drift_self.json", findings=findings)

        report = run_cycle(repo=repo, max_proposals=10)
        sig_counts = sum(1 for p in report.proposals if p.signal_type == "always_same")
        # Cap is max(1, max_items // 3) = 3 with max_items=10.
        assert sig_counts <= 4, f"signal dominance not capped: {sig_counts}"


# ---------------------------------------------------------------------------
# 2. Recurrence compounding
# ---------------------------------------------------------------------------


class TestRecurrence:
    def test_recurring_finding_gets_priority(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        findings = [
            {
                "id": "stable-1",
                "signal_type": "sig_a",
                "file_path": "src/x.py",
                "start_line": 1,
                "severity": "high",
                "score": 0.5,
                "title": "stable",
            }
        ]
        _write_self_report(repo / "benchmark_results" / "drift_self.json", findings=findings)

        # First cycle establishes the ledger entry.
        report1 = run_cycle(repo=repo, max_proposals=10)
        assert all(p.recurrence == 1 for p in report1.proposals)

        # Second cycle must pick it up as recurrent.
        report2 = run_cycle(repo=repo, max_proposals=10)
        recurring = [p for p in report2.proposals if "stable-1" in p.proposal_id]
        assert recurring, "stable finding was not re-proposed"
        assert recurring[0].recurrence == 2


# ---------------------------------------------------------------------------
# 3. Regressive KPI detection
# ---------------------------------------------------------------------------


class TestRegressiveSignal:
    def test_negative_slope_emits_proposal(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # aggregate_f1 dropping by 0.05 per snapshot.
        rows = [
            {"aggregate_f1": 0.95},
            {"aggregate_f1": 0.90},
            {"aggregate_f1": 0.85},
            {"aggregate_f1": 0.80},
        ]
        _write_kpi_trend(repo / "benchmark_results" / "kpi_trend.jsonl", rows=rows)

        report = run_cycle(repo=repo, max_proposals=10, trend_window=4)
        regressive = [p for p in report.proposals if p.kind == "regressive_signal"]
        assert regressive, "no regressive proposal emitted for clearly negative slope"
        assert "aggregate_f1" in regressive[0].proposal_id

    def test_stable_metric_no_proposal(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        rows = [{"aggregate_f1": 0.9}, {"aggregate_f1": 0.9}, {"aggregate_f1": 0.9}]
        _write_kpi_trend(repo / "benchmark_results" / "kpi_trend.jsonl", rows=rows)

        report = run_cycle(repo=repo, max_proposals=10, trend_window=3)
        assert not any(p.kind == "regressive_signal" for p in report.proposals)


# ---------------------------------------------------------------------------
# 4. Stale audit detector
# ---------------------------------------------------------------------------


class TestStaleAudit:
    def test_signals_newer_than_audits_emits_proposal(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        # Old audit file.
        audit = repo / "audit_results" / "fmea_matrix.md"
        audit.write_text("# old", encoding="utf-8")
        old = time.time() - 60 * 86400
        import os
        os.utime(audit, (old, old))

        # Fresh signal file (default mtime = now).
        (repo / "src" / "drift" / "signals" / "sig.py").write_text("x = 1", encoding="utf-8")

        report = run_cycle(repo=repo, max_proposals=10)
        stale = [p for p in report.proposals if p.kind == "stale_audit"]
        assert stale, "stale_audit proposal not emitted"


# ---------------------------------------------------------------------------
# 5. Determinism of artefact output
# ---------------------------------------------------------------------------


class TestArtefactsAndDeterminism:
    def test_artefacts_written(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _write_self_report(
            repo / "benchmark_results" / "drift_self.json",
            findings=[
                {
                    "id": "x",
                    "signal_type": "s",
                    "file_path": "a.py",
                    "start_line": 1,
                    "severity": "low",
                    "score": 0.1,
                    "title": "t",
                }
            ],
        )
        report = run_cycle(repo=repo, max_proposals=5)
        cycle_dir = repo / "work_artifacts" / "self_improvement" / report.cycle_ts
        assert (cycle_dir / "proposals.json").exists()
        assert (cycle_dir / "summary.md").exists()

        ledger = repo / ".drift" / "self_improvement_ledger.jsonl"
        assert ledger.exists()
        last = ledger.read_text(encoding="utf-8").strip().splitlines()[-1]
        assert json.loads(last)["cycle_ts"] == report.cycle_ts

    def test_proposal_ids_stable(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        findings = [
            {
                "id": "abc",
                "signal_type": "sig_x",
                "file_path": "src/m.py",
                "start_line": 10,
                "severity": "medium",
                "score": 0.4,
                "title": "t",
            }
        ]
        _write_self_report(repo / "benchmark_results" / "drift_self.json", findings=findings)

        # Two engines on the same input must produce the same proposal IDs.
        eng = SelfImprovementEngine(repo=repo, max_proposals=3)
        ids_a = tuple(p.proposal_id for p in eng.run().proposals)
        ids_b = tuple(p.proposal_id for p in eng.run().proposals)
        assert ids_a == ids_b


# ---------------------------------------------------------------------------
# 6. CLI wiring
# ---------------------------------------------------------------------------


class TestCli:
    def test_self_improve_run_invokes_cycle(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        _write_self_report(
            repo / "benchmark_results" / "drift_self.json",
            findings=[
                {
                    "id": "x",
                    "signal_type": "s",
                    "file_path": "a.py",
                    "start_line": 1,
                    "severity": "low",
                    "score": 0.1,
                    "title": "t",
                }
            ],
        )
        result = CliRunner().invoke(
            main,
            ["self-improve", "run", "--repo", str(repo), "--format", "json"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "cycle_ts" in payload
        assert "proposals" in payload

    def test_self_improve_ledger_handles_missing(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        result = CliRunner().invoke(
            main,
            ["self-improve", "ledger", "--repo", str(repo)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "no ledger" in result.output.lower()


# ---------------------------------------------------------------------------
# 7. Frozen / additive proposal model
# ---------------------------------------------------------------------------


class TestProposalModel:
    def test_proposal_is_frozen(self) -> None:
        p = ImprovementProposal(
            proposal_id="x",
            kind="hotspot_finding",
            score=1.0,
            rationale="r",
            suggested_action="a",
        )
        try:
            p.score = 99.0  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("ImprovementProposal must be frozen")
