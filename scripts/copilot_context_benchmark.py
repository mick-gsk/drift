#!/usr/bin/env python3
"""Copilot-Context Coverage Benchmark.

Measures whether ``generate_instructions()`` translates detected drift
findings into correct, actionable Copilot instructions for known
ground-truth fixtures.

Metrics
-------
- **instruction_coverage_rate** — fraction of actionable TP signals that
  produce a matching instruction section.
- **noise_rate** — fraction of TN-only signals that erroneously produce
  instructions.
- **file_reference_rate** — fraction of generated instruction sections that
  reference at least one affected file.
- **specificity_score** — fraction of instruction sections that contain a
  concrete fix / remediation line.

Run::

    python scripts/copilot_context_benchmark.py
"""

from __future__ import annotations

import datetime
import json
import sys
import tempfile
from pathlib import Path

# Ensure the project root is importable when running as a script.
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root / "src"))
sys.path.insert(0, str(_project_root))

import drift.signals.architecture_violation  # noqa: E402, F401  # isort: skip
import drift.signals.broad_exception_monoculture  # noqa: E402, F401
import drift.signals.cohesion_deficit  # noqa: E402, F401
import drift.signals.doc_impl_drift  # noqa: E402, F401
import drift.signals.explainability_deficit  # noqa: E402, F401
import drift.signals.guard_clause_deficit  # noqa: E402, F401
import drift.signals.mutant_duplicates  # noqa: E402, F401
import drift.signals.pattern_fragmentation  # noqa: E402, F401
import drift.signals.system_misalignment  # noqa: E402, F401
import drift.signals.temporal_volatility  # noqa: E402, F401
import drift.signals.test_polarity_deficit  # noqa: E402, F401
from drift.config import DriftConfig  # noqa: E402
from drift.copilot_context import generate_instructions  # noqa: E402
from drift.ingestion.ast_parser import parse_file  # noqa: E402
from drift.ingestion.file_discovery import discover_files  # noqa: E402
from drift.models import (  # noqa: E402
    FileHistory,
    Finding,
    ParseResult,
    RepoAnalysis,
    SignalType,
)
from drift.signals.base import AnalysisContext, create_signals  # noqa: E402
from tests.fixtures.ground_truth import (  # noqa: E402
    FIXTURES_BY_SIGNAL,
    GroundTruthFixture,
)

# ---------------------------------------------------------------------------
# Signal → expected section heading mapping
# ---------------------------------------------------------------------------

SIGNAL_SECTION_MAP: dict[SignalType, str] = {
    SignalType.ARCHITECTURE_VIOLATION: "Layer Boundaries",
    SignalType.PATTERN_FRAGMENTATION: "Code Pattern Consistency",
    SignalType.NAMING_CONTRACT_VIOLATION: "Naming Conventions",
    SignalType.GUARD_CLAUSE_DEFICIT: "Input Validation",
    SignalType.BROAD_EXCEPTION_MONOCULTURE: "Exception Handling",
    SignalType.DOC_IMPL_DRIFT: "Documentation Alignment",
    SignalType.MUTANT_DUPLICATE: "Deduplication",
    SignalType.EXPLAINABILITY_DEFICIT: "Code Documentation",
    SignalType.BYPASS_ACCUMULATION: "TODO/FIXME Hygiene",
    SignalType.EXCEPTION_CONTRACT_DRIFT: "Exception Contracts",
}


# ---------------------------------------------------------------------------
# Fixture → Findings pipeline (mirrors test_precision_recall.py)
# ---------------------------------------------------------------------------


def _run_signals_on_fixture(
    fixture: GroundTruthFixture,
    tmp_dir: Path,
    signal_filter: set[SignalType] | None = None,
) -> list[Finding]:
    """Materialize a fixture, parse it, run signal detectors."""
    fixture_dir = fixture.materialize(tmp_dir)

    config = DriftConfig(
        include=["**/*.py"],
        exclude=["**/__pycache__/**"],
        embeddings_enabled=False,
    )

    files = discover_files(fixture_dir, config.include, config.exclude)
    parse_results: list[ParseResult] = []
    for finfo in files:
        pr = parse_file(finfo.path, fixture_dir, finfo.language)
        parse_results.append(pr)

    file_histories: dict[str, FileHistory] = {}
    for finfo in files:
        key = finfo.path.as_posix()
        is_new = "new_feature" in key or "new_func" in key
        override = fixture.file_history_overrides.get(key)

        file_histories[key] = FileHistory(
            path=finfo.path,
            total_commits=(
                override.total_commits
                if override and override.total_commits is not None
                else (1 if is_new else 10)
            ),
            unique_authors=(
                override.unique_authors
                if override and override.unique_authors is not None
                else 1
            ),
            ai_attributed_commits=(
                override.ai_attributed_commits
                if override and override.ai_attributed_commits is not None
                else 0
            ),
            change_frequency_30d=(
                override.change_frequency_30d
                if override and override.change_frequency_30d is not None
                else (5.0 if is_new else 0.5)
            ),
            defect_correlated_commits=(
                override.defect_correlated_commits
                if override and override.defect_correlated_commits is not None
                else 0
            ),
            last_modified=(
                datetime.datetime.now(tz=datetime.UTC)
                if is_new
                else datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=60)
            ),
            first_seen=(
                datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=3)
                if is_new
                else datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=120)
            ),
        )

    ctx = AnalysisContext(
        repo_path=fixture_dir,
        config=config,
        parse_results=parse_results,
        file_histories=file_histories,
        embedding_service=None,
    )

    signals = create_signals(ctx)
    if signal_filter:
        signals = [s for s in signals if s.signal_type in signal_filter]

    all_findings: list[Finding] = []
    for signal in signals:
        try:
            findings = signal.analyze(parse_results, file_histories, config)
            all_findings.extend(findings)
        except Exception:
            pass
    return all_findings


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------


def _build_aggregated_analysis(findings: list[Finding]) -> RepoAnalysis:
    """Build a synthetic RepoAnalysis from a flat finding list."""
    score = max((f.score for f in findings), default=0.0) if findings else 0.0
    return RepoAnalysis(
        repo_path=Path("."),
        analyzed_at=datetime.datetime.now(tz=datetime.UTC),
        drift_score=score,
        findings=findings,
    )


def _section_has_file_reference(section_text: str) -> bool:
    """Check whether the section references at least one file path."""
    # Look for backtick-wrapped paths (e.g. `services/handler_a.py`)
    return "`" in section_text and ("/" in section_text or ".py" in section_text)


def _section_has_remediation(section_text: str) -> bool:
    """Check whether the section has a concrete remediation line (not just a heading)."""
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") and not stripped.startswith("- **"):
            return True
    return False


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------


def run_benchmark() -> dict:
    """Execute the full benchmark and return the evidence dict."""
    per_signal: dict[str, dict] = {}
    failures: list[dict] = []
    signal_instructions_ok = 0
    signal_instructions_total = 0
    signal_noise_hits = 0
    signal_noise_total = 0
    file_ref_hits = 0
    specificity_hits = 0
    sections_total = 0

    with tempfile.TemporaryDirectory() as tmp_root:
        tmp_path = Path(tmp_root)

        for signal_type in sorted(SIGNAL_SECTION_MAP, key=lambda s: s.value):
            expected_heading = SIGNAL_SECTION_MAP[signal_type]
            fixtures = FIXTURES_BY_SIGNAL.get(signal_type, [])
            if not fixtures:
                per_signal[signal_type.value] = {
                    "coverage": None,
                    "fixtures": 0,
                    "reason": "no fixtures",
                }
                continue

            # Split TP / TN fixtures for this signal
            tp_fixtures = [
                f
                for f in fixtures
                if any(
                    e.signal_type == signal_type and e.should_detect for e in f.expected
                )
            ]
            tn_fixtures = [
                f
                for f in fixtures
                if all(
                    not (e.signal_type == signal_type and e.should_detect) for e in f.expected
                )
            ]

            # --- TP evaluation: aggregate all TP fixtures for this signal ---
            aggregated_findings: list[Finding] = []
            fixture_names_tp: list[str] = []
            for fix in tp_fixtures:
                findings = _run_signals_on_fixture(
                    fix, tmp_path, signal_filter={signal_type}
                )
                aggregated_findings.extend(findings)
                fixture_names_tp.append(fix.name)

            # Generate instructions from aggregated findings
            analysis = _build_aggregated_analysis(aggregated_findings)
            instructions = generate_instructions(analysis)

            # Check: does the expected heading appear?
            heading_found = f"### {expected_heading}" in instructions
            if heading_found:
                signal_instructions_ok += 1
            else:
                # Determine failure reason
                actionable_findings = [
                    f
                    for f in aggregated_findings
                    if f.signal_type == signal_type and f.score >= 0.4
                ]
                if not actionable_findings:
                    reason = "no findings above score threshold"
                elif len(actionable_findings) < 2:
                    reason = "below min_finding_count (need >=2)"
                else:
                    reason = "heading not in output"
                failures.append({
                    "signal": signal_type.value,
                    "fixtures": fixture_names_tp,
                    "findings_count": len(actionable_findings),
                    "reason": reason,
                })
            signal_instructions_total += 1

            # Extract the section for quality metrics
            if heading_found:
                sections_total += 1
                # Extract from heading to next ### or end-of-markers
                start_idx = instructions.index(f"### {expected_heading}")
                rest = instructions[start_idx:]
                next_heading = rest.find("\n### ", 4)
                section_text = rest[:next_heading] if next_heading > 0 else rest

                if _section_has_file_reference(section_text):
                    file_ref_hits += 1
                if _section_has_remediation(section_text):
                    specificity_hits += 1

            # --- TN evaluation: each TN fixture individually ---
            for tn_fix in tn_fixtures:
                tn_findings = _run_signals_on_fixture(
                    tn_fix, tmp_path, signal_filter={signal_type}
                )
                tn_analysis = _build_aggregated_analysis(tn_findings)
                tn_instructions = generate_instructions(tn_analysis)
                if f"### {expected_heading}" in tn_instructions:
                    signal_noise_hits += 1
                    failures.append({
                        "signal": signal_type.value,
                        "fixture": tn_fix.name,
                        "reason": "instruction generated for TN fixture",
                    })
                signal_noise_total += 1

            per_signal[signal_type.value] = {
                "coverage": 1.0 if heading_found else 0.0,
                "tp_fixtures": len(tp_fixtures),
                "tn_fixtures": len(tn_fixtures),
                "aggregated_findings": len(aggregated_findings),
                "heading_found": heading_found,
            }

    # Compute aggregate metrics
    icr = (
        signal_instructions_ok / signal_instructions_total
        if signal_instructions_total
        else 0.0
    )
    noise = signal_noise_hits / signal_noise_total if signal_noise_total else 0.0
    file_ref = file_ref_hits / sections_total if sections_total else 0.0
    specificity = specificity_hits / sections_total if sections_total else 0.0

    evidence = {
        "version": "0.8.2",
        "date": datetime.date.today().isoformat(),
        "benchmark": "copilot_context_coverage",
        "metrics": {
            "instruction_coverage_rate": round(icr, 4),
            "noise_rate": round(noise, 4),
            "file_reference_rate": round(file_ref, 4),
            "specificity_score": round(specificity, 4),
            "signals_tested": signal_instructions_total,
            "signals_with_instruction": signal_instructions_ok,
            "tn_checks": signal_noise_total,
            "tn_false_instructions": signal_noise_hits,
            "sections_evaluated": sections_total,
        },
        "per_signal": per_signal,
        "failures": failures,
    }
    return evidence


# ---------------------------------------------------------------------------
# Terminal report
# ---------------------------------------------------------------------------


def print_report(evidence: dict) -> None:
    """Print a summary table to stdout."""
    m = evidence["metrics"]
    print("=" * 68)
    print("  Copilot-Context Coverage Benchmark")
    print("=" * 68)
    print()

    # Per-signal table
    print(f"{'Signal':<32} {'TP Fx':>5} {'TN Fx':>5} {'Covered':>8}")
    print("-" * 55)
    for sig, info in sorted(evidence["per_signal"].items()):
        tp = info.get("tp_fixtures", 0)
        tn = info.get("tn_fixtures", 0)
        cov = info.get("coverage")
        cov_str = f"{cov:.0%}" if cov is not None else "n/a"
        mark = "ok" if cov == 1.0 else ("MISS" if cov == 0.0 else "n/a")
        print(f"  {sig:<30} {tp:>5} {tn:>5} {cov_str:>6}  {mark}")
    print()

    # Summary
    print(f"  Instruction Coverage Rate : {m['instruction_coverage_rate']:.1%}")
    print(f"  Noise Rate                : {m['noise_rate']:.1%}")
    print(f"  File Reference Rate       : {m['file_reference_rate']:.1%}")
    print(f"  Specificity Score         : {m['specificity_score']:.1%}")
    print()

    if evidence["failures"]:
        print("  Failures:")
        for fail in evidence["failures"]:
            sig = fail["signal"]
            reason = fail["reason"]
            print(f"    - {sig}: {reason}")
        print()

    ok = m["instruction_coverage_rate"] >= 0.70 and m["noise_rate"] == 0.0
    verdict = "PASS" if ok else "FAIL"
    print(f"  Verdict: {verdict}")
    print("=" * 68)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    evidence = run_benchmark()
    print_report(evidence)

    # Write evidence JSON
    out_path = _project_root / "benchmark_results" / "copilot_context_evidence.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\n  Evidence written to: {out_path}")


if __name__ == "__main__":
    main()
