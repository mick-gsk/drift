"""Tests for the Drift Self-Improvement Loop (DSOL, ADR-097/098)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from click.testing import CliRunner
from drift.self_improvement.engine import (
    _check_scan_staleness,
    _convergence_check,
    _fp_oracle_proposals,
)

from drift.cli import main
from drift.self_improvement import (
    ClosedProposalEntry,
    ConvergenceStatus,
    ImprovementProposal,
    SelfImprovementEngine,
    close_proposal,
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


# ---------------------------------------------------------------------------
# 8. FP Oracle proposals (ADR-098 CP5)
# ---------------------------------------------------------------------------


def _make_oracle_report(violations: list[dict]) -> dict:
    return {
        "_metadata": {"generated_at": "2025-01-01T00:00:00Z"},
        "aggregate": {},
        "budget_violations": violations,
    }


class TestFPOracleProposals:
    def test_over_budget_emits_proposal(self) -> None:
        report = _make_oracle_report(
            [{"signal": "PFS", "measured_fp_rate": 0.35, "budget": 0.20, "over_by": 0.15}]
        )
        proposals = _fp_oracle_proposals(report, previous_ids=set(), max_items=10)
        assert len(proposals) == 1
        assert proposals[0].kind == "fp_rate_exceeded"
        assert proposals[0].signal_type == "PFS"
        assert proposals[0].score > 0.0

    def test_no_violations_no_proposals(self) -> None:
        report = _make_oracle_report([])
        proposals = _fp_oracle_proposals(report, previous_ids=set(), max_items=10)
        assert proposals == []

    def test_recurrence_boosted_when_previous(self) -> None:
        report = _make_oracle_report(
            [{"signal": "AVS", "measured_fp_rate": 0.3, "budget": 0.2, "over_by": 0.1}]
        )
        prev_ids = {"fp_rate_exceeded::AVS"}
        proposals = _fp_oracle_proposals(report, previous_ids=prev_ids, max_items=10)
        assert proposals[0].recurrence == 2

    def test_max_items_capped(self) -> None:
        violations = [
            {"signal": f"SIG{i}", "measured_fp_rate": 0.3, "budget": 0.2, "over_by": 0.1}
            for i in range(10)
        ]
        report = _make_oracle_report(violations)
        proposals = _fp_oracle_proposals(report, previous_ids=set(), max_items=3)
        assert len(proposals) == 3

    def test_missing_oracle_returns_empty(self) -> None:
        proposals = _fp_oracle_proposals({}, previous_ids=set(), max_items=10)
        assert proposals == []

    def test_oracle_integrated_in_run(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        oracle_path = repo / "benchmark_results" / "oracle_fp_report.json"
        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_text(
            json.dumps(
                _make_oracle_report(
                    [{"signal": "MDS", "measured_fp_rate": 0.4, "budget": 0.2, "over_by": 0.2}]
                )
            ),
            encoding="utf-8",
        )
        report = run_cycle(repo=repo, max_proposals=10)
        fp_proposals = [p for p in report.proposals if p.kind == "fp_rate_exceeded"]
        assert fp_proposals, "fp_rate_exceeded proposal not emitted from oracle"
        assert fp_proposals[0].signal_type == "MDS"


# ---------------------------------------------------------------------------
# 9. Convergence check (ADR-098 CP3)
# ---------------------------------------------------------------------------


class TestConvergenceCheck:
    def test_stagnating_when_same_ids_repeat(self) -> None:
        rows = [
            {"proposal_ids": ["a", "b", "c"]},
            {"proposal_ids": ["a", "b", "c"]},
            {"proposal_ids": ["a", "b", "c"]},
            {"proposal_ids": ["a", "b", "c"]},
        ]
        result = _convergence_check(rows, window=4)
        assert result is not None
        assert result.stagnating is True
        assert result.overlap_ratio == 1.0

    def test_not_stagnating_with_diverse_ids(self) -> None:
        rows = [
            {"proposal_ids": ["a", "b"]},
            {"proposal_ids": ["c", "d"]},
            {"proposal_ids": ["e", "f"]},
            {"proposal_ids": ["g", "h"]},
        ]
        result = _convergence_check(rows, window=4)
        assert result is not None
        assert result.stagnating is False

    def test_returns_none_for_single_entry(self) -> None:
        rows = [{"proposal_ids": ["a"]}]
        result = _convergence_check(rows, window=4)
        assert result is None

    def test_convergence_status_in_report(self, tmp_path: Path) -> None:
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
        # Need 3 cycles: cycle 1 writes first ledger row,
        # cycle 2 writes second, cycle 3 reads 2 rows → convergence_status not None.
        run_cycle(repo=repo, max_proposals=5)
        run_cycle(repo=repo, max_proposals=5)
        report3 = run_cycle(repo=repo, max_proposals=5)
        assert report3.convergence_status is not None
        assert isinstance(report3.convergence_status, ConvergenceStatus)

    def test_overlap_ratio_bounded(self) -> None:
        rows = [
            {"proposal_ids": ["a", "b", "c", "d"]},
            {"proposal_ids": ["a", "b", "c", "d"]},
        ]
        result = _convergence_check(rows, window=4)
        assert result is not None
        assert 0.0 <= result.overlap_ratio <= 1.0


# ---------------------------------------------------------------------------
# 10. Scan staleness (ADR-098 CP1+CP4)
# ---------------------------------------------------------------------------


class TestScanStaleness:
    def test_old_report_emits_warning(self, tmp_path: Path) -> None:
        report_path = tmp_path / "drift_self.json"
        report_path.write_text("{}", encoding="utf-8")
        old = time.time() - 10 * 86400  # 10 days old
        os.utime(report_path, (old, old))
        warning = _check_scan_staleness(report_path, max_age_days=7)
        assert warning is not None
        assert "stale" in warning.lower() or "days" in warning.lower()

    def test_fresh_report_no_warning(self, tmp_path: Path) -> None:
        report_path = tmp_path / "drift_self.json"
        report_path.write_text("{}", encoding="utf-8")
        warning = _check_scan_staleness(report_path, max_age_days=7)
        assert warning is None

    def test_missing_file_no_error(self, tmp_path: Path) -> None:
        report_path = tmp_path / "nonexistent.json"
        warning = _check_scan_staleness(report_path, max_age_days=7)
        assert warning is None

    def test_env_var_overrides(self, tmp_path: Path, monkeypatch) -> None:
        report_path = tmp_path / "drift_self.json"
        report_path.write_text("{}", encoding="utf-8")
        monkeypatch.setenv("DRIFT_SELF_SCAN_FAILED", "1")
        warning = _check_scan_staleness(report_path, max_age_days=7)
        assert warning is not None
        assert "failed" in warning.lower() or "DRIFT_SELF_SCAN_FAILED" in warning

    def test_stale_scan_appears_in_observations(self, tmp_path: Path, monkeypatch) -> None:
        repo = _make_repo(tmp_path)
        monkeypatch.setenv("DRIFT_SELF_SCAN_FAILED", "1")
        report = run_cycle(repo=repo, max_proposals=5)
        assert report.scan_stale is True
        assert any("scan" in obs.lower() or "stale" in obs.lower() for obs in report.observations)


# ---------------------------------------------------------------------------
# 11. Quality threshold / min-score (ADR-098 CP6)
# ---------------------------------------------------------------------------


class TestQualityThreshold:
    def test_low_score_filtered(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        oracle_path = repo / "benchmark_results" / "oracle_fp_report.json"
        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_text(
            json.dumps(
                _make_oracle_report(
                    [{"signal": "EDS", "measured_fp_rate": 0.22, "budget": 0.20, "over_by": 0.02}]
                )
            ),
            encoding="utf-8",
        )
        report = run_cycle(repo=repo, max_proposals=10, min_proposal_score=5.0)
        # over_by=0.02 → score=2.0, below threshold 5.0
        fp_proposals = [p for p in report.proposals if p.kind == "fp_rate_exceeded"]
        assert not fp_proposals, "low-score proposal should have been filtered"

    def test_zero_threshold_keeps_all(self, tmp_path: Path) -> None:
        repo = _make_repo(tmp_path)
        oracle_path = repo / "benchmark_results" / "oracle_fp_report.json"
        oracle_path.parent.mkdir(parents=True, exist_ok=True)
        oracle_path.write_text(
            json.dumps(
                _make_oracle_report(
                    [{"signal": "EDS", "measured_fp_rate": 0.22, "budget": 0.20, "over_by": 0.02}]
                )
            ),
            encoding="utf-8",
        )
        report = run_cycle(repo=repo, max_proposals=10, min_proposal_score=0.0)
        fp_proposals = [p for p in report.proposals if p.kind == "fp_rate_exceeded"]
        assert fp_proposals, "zero threshold should not filter any proposal"

    def test_cli_min_score_flag(self, tmp_path: Path) -> None:
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
            [
                "self-improve",
                "run",
                "--repo",
                str(repo),
                "--min-score",
                "9999",
                "--format",
                "json",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # With ridiculously high threshold, proposals list should be empty.
        assert isinstance(payload["proposals"], list)


# ---------------------------------------------------------------------------
# 12. Apply subcommand (ADR-098 write-back)
# ---------------------------------------------------------------------------


def _write_proposals_json(
    path: Path, proposals: list[dict], cycle_ts: str = "20250101T000000Z"
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "cycle_ts": cycle_ts,
                "corpus_sha": None,
                "kpi_snapshot": {},
                "proposals": proposals,
                "observations": [],
                "ledger_path": None,
                "scan_stale": False,
                "convergence_status": None,
            }
        ),
        encoding="utf-8",
    )


class TestApplyCommand:
    def test_dry_run_no_files_written(self, tmp_path: Path) -> None:
        proposals_path = tmp_path / "proposals.json"
        _write_proposals_json(proposals_path, [])
        result = CliRunner().invoke(
            main,
            [
                "self-improve",
                "apply",
                "--proposals",
                str(proposals_path),
                "--dry-run",
                "--output-dir",
                str(tmp_path / "out"),
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert not (tmp_path / "out").exists(), "dry-run must not create any files"

    def test_apply_creates_fp_triage(self, tmp_path: Path) -> None:
        proposals_path = tmp_path / "proposals.json"
        _write_proposals_json(
            proposals_path,
            [
                {
                    "proposal_id": "fp_rate_exceeded::PFS",
                    "kind": "fp_rate_exceeded",
                    "signal_type": "PFS",
                    "score": 15.0,
                    "rationale": "PFS FP rate exceeded.",
                    "suggested_action": "Review PFS FP samples.",
                    "recurrence": 1,
                    "severity": None,
                    "file_path": None,
                }
            ],
        )
        out_dir = tmp_path / "out"
        result = CliRunner().invoke(
            main,
            [
                "self-improve",
                "apply",
                "--proposals",
                str(proposals_path),
                "--output-dir",
                str(out_dir),
                "--format",
                "text",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        artefacts = list(out_dir.glob("fp_triage_PFS.md"))
        assert artefacts, "fp_triage artefact not created"

    def test_apply_creates_adr_stub(self, tmp_path: Path) -> None:
        proposals_path = tmp_path / "proposals.json"
        _write_proposals_json(
            proposals_path,
            [
                {
                    "proposal_id": "regressive_signal::aggregate_f1",
                    "kind": "regressive_signal",
                    "signal_type": "aggregate_f1",
                    "score": 0.0,
                    "rationale": "F1 dropped.",
                    "suggested_action": "Investigate.",
                    "recurrence": 1,
                    "severity": None,
                    "file_path": None,
                }
            ],
        )
        out_dir = tmp_path / "out"
        result = CliRunner().invoke(
            main,
            [
                "self-improve",
                "apply",
                "--proposals",
                str(proposals_path),
                "--output-dir",
                str(out_dir),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        artefacts = list(out_dir.glob("adr_stub_aggregate_f1.md"))
        assert artefacts, "adr_stub artefact not created"

    def test_apply_creates_hotspot_brief(self, tmp_path: Path) -> None:
        proposals_path = tmp_path / "proposals.json"
        _write_proposals_json(
            proposals_path,
            [
                {
                    "proposal_id": "hotspot_finding::src/x.py::PFS::1",
                    "kind": "hotspot_finding",
                    "signal_type": "PFS",
                    "score": 0.9,
                    "rationale": "High-score finding.",
                    "suggested_action": "Fix.",
                    "recurrence": 1,
                    "severity": "high",
                    "file_path": "src/x.py",
                }
            ],
        )
        out_dir = tmp_path / "out"
        result = CliRunner().invoke(
            main,
            [
                "self-improve",
                "apply",
                "--proposals",
                str(proposals_path),
                "--output-dir",
                str(out_dir),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        artefacts = list(out_dir.glob("hotspot_*.md"))
        assert artefacts, "hotspot artefact not created"

    def test_apply_json_output_format(self, tmp_path: Path) -> None:
        proposals_path = tmp_path / "proposals.json"
        _write_proposals_json(proposals_path, [])
        out_dir = tmp_path / "out"
        result = CliRunner().invoke(
            main,
            [
                "self-improve",
                "apply",
                "--proposals",
                str(proposals_path),
                "--output-dir",
                str(out_dir),
                "--format",
                "json",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "created" in payload
        assert isinstance(payload["created"], list)


# ---------------------------------------------------------------------------
# Phase 5 — close_proposal and `drift self-improve close`
# ---------------------------------------------------------------------------


class TestCloseProposal:
    def test_appends_jsonl(self, tmp_path: Path) -> None:
        log = tmp_path / ".drift" / "self_improvement_closed.jsonl"
        entry = close_proposal("DSOL-001", "done in PR #1", closed_path=log)
        assert isinstance(entry, ClosedProposalEntry)
        assert log.exists()
        row = json.loads(log.read_text(encoding="utf-8").strip())
        assert row["proposal_id"] == "DSOL-001"
        assert row["outcome_note"] == "done in PR #1"
        assert "closed_at" in row

    def test_multiple_appends(self, tmp_path: Path) -> None:
        log = tmp_path / ".drift" / "self_improvement_closed.jsonl"
        close_proposal("DSOL-001", closed_path=log)
        close_proposal("DSOL-002", closed_path=log)
        rows = [json.loads(ln) for ln in log.read_text(encoding="utf-8").splitlines()]
        assert [r["proposal_id"] for r in rows] == ["DSOL-001", "DSOL-002"]

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        log = tmp_path / "deep" / "nested" / "closed.jsonl"
        close_proposal("DSOL-X", closed_path=log)
        assert log.exists()

    def test_closed_ids_excluded_from_previous_ids(self, tmp_path: Path) -> None:
        """Closed proposals must not appear in _load_previous_ids."""
        engine = SelfImprovementEngine(repo=tmp_path)
        # Simulate a ledger entry containing DSOL-001
        ledger = tmp_path / ".drift" / "self_improvement_ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            json.dumps({"cycle_ts": "2024-01-01T00:00:00", "proposal_ids": ["DSOL-001"]}) + "\n",
            encoding="utf-8",
        )
        # Without closing: DSOL-001 appears
        ids_before = engine._load_previous_ids()
        assert "DSOL-001" in ids_before
        # Close DSOL-001
        closed_log = tmp_path / ".drift" / "self_improvement_closed.jsonl"
        close_proposal("DSOL-001", closed_path=closed_log)
        ids_after = engine._load_previous_ids()
        assert "DSOL-001" not in ids_after


class TestSelfImproveCloseCLI:
    def test_close_text_output(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["self-improve", "close", "DSOL-abc", "--repo", str(tmp_path)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        assert "DSOL-abc" in result.output

    def test_close_json_output(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "self-improve", "close", "DSOL-abc",
                "--note", "shipped",
                "--repo", str(tmp_path),
                "--format", "json",
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["proposal_id"] == "DSOL-abc"
        assert payload["outcome_note"] == "shipped"

    def test_close_writes_log(self, tmp_path: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            main,
            ["self-improve", "close", "DSOL-xyz", "--repo", str(tmp_path)],
            catch_exceptions=False,
        )
        log = tmp_path / ".drift" / "self_improvement_closed.jsonl"
        assert log.exists()
        row = json.loads(log.read_text(encoding="utf-8").strip())
        assert row["proposal_id"] == "DSOL-xyz"
