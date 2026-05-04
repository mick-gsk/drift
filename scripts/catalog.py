#!/usr/bin/env python3
"""List script files with short descriptions.

Examples:
    python scripts/catalog.py
    python scripts/catalog.py --search evidence
    python scripts/catalog.py --json
    python scripts/catalog.py --category gate
    python scripts/catalog.py --category benchmark

Categories:
    gate        Pre-push / CI validators and checks (check_*, validate_*, *_gate.py)
    generator   Deterministic artifact generators (generate_*, sync_*, integrate_*)
    benchmark   Evaluation harnesses and benchmarks (benchmark_*, ab_harness, mutation_*)
    ops         Operational tools: release, KPIs, maintenance, session, triage
    analysis    Research, studies, one-off analyses (_*analysis, study_*, ablation_*)
    experimental Temporary / experimental scripts (_tmp_*, experiment_*, media scripts)
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# Canonical category assignment for all scripts in this directory.
# Categories: gate | generator | benchmark | ops | analysis | experimental
SCRIPT_CATEGORIES: dict[str, str] = {
    # --- gates ---
    "check_agent_harness_contract.py": "gate",
    "check_blast_radius_gate.py": "gate",
    "check_doc_links.py": "gate",
    "check_dsol_convergence.py": "gate",
    "check_model_consistency.py": "gate",
    "check_negative_patterns.py": "gate",
    "check_policy_gate.py": "gate",
    "check_release_discipline.py": "gate",
    "check_repo_hygiene.py": "gate",
    "check_risk_audit.py": "gate",
    "check_schema_compat.py": "gate",
    "check_version.py": "gate",
    "ecosystem_check.py": "gate",
    "kpi_trend_gate.py": "gate",
    "nudge_gate.py": "gate",
    "perf_gate.py": "gate",
    "ratchet_coverage.py": "gate",
    "release_risk_gate.py": "gate",
    "validate_adr_frontmatter.py": "gate",
    "validate_feature_evidence.py": "gate",
    "validate_negative_patterns.py": "gate",
    "validate_proposals.py": "gate",
    "validate_task_spec.py": "gate",
    "verify_gate_not_bypassed.py": "gate",
    "gate_check.py": "gate",
    # --- generators ---
    "build_instruction_registry.py": "generator",
    "generate_agent_tasks_evidence.py": "generator",
    "generate_annotation_sheet.py": "generator",
    "generate_benchmark_baseline.py": "generator",
    "generate_changelog_entry.py": "generator",
    "generate_engine_stubs.py": "generator",
    "generate_evidence_schema.py": "generator",
    "generate_feature_evidence.py": "generator",
    "generate_llms_txt.py": "generator",
    "generate_output_schema.py": "generator",
    "generate_pr_baseline.py": "generator",
    "generate_repair_coverage_matrix.py": "generator",
    "integrate_changelog_entry.py": "generator",
    "sync_version.py": "generator",
    "update_work_artifacts_index.py": "generator",
    # --- benchmarks ---
    "ab_harness.py": "benchmark",
    "adversarial_brief_audit.py": "benchmark",
    "benchmark.py": "benchmark",
    "benchmark_agent_loop.py": "benchmark",
    "benchmark_cross_version.py": "benchmark",
    "benchmark_mcp_perf.py": "benchmark",
    "benchmark_perf.py": "benchmark",
    "benchmark_repos.py": "benchmark",
    "benchmark_typescript.py": "benchmark",
    "brief_ab_study.py": "benchmark",
    "copilot_behavioral_benchmark.py": "benchmark",
    "copilot_context_benchmark.py": "benchmark",
    "corpus_scan.py": "benchmark",
    "defect_corpus_benchmark.py": "benchmark",
    "evaluate_benchmark.py": "benchmark",
    "holdout_validation.py": "benchmark",
    "mirror_ab_study.py": "benchmark",
    "mutation_benchmark.py": "benchmark",
    "mutation_gap_report.py": "benchmark",
    "repair_benchmark.py": "benchmark",
    "repair_eval.py": "benchmark",
    "replay_benchmark.py": "benchmark",
    "run_agent_loop_benchmark.py": "benchmark",
    "signal_mutation_test.py": "benchmark",
    "_bench_utils.py": "benchmark",
    "_mirror_experiment.py": "benchmark",
    "_mutation_benchmark.py": "benchmark",
    # --- ops ---
    "agent_repro_bundle.py": "ops",
    "catalog.py": "ops",
    "ci_drift_trend_alert.py": "ops",
    "ci_fp_threshold_alert.py": "ops",
    "collect_kpi_snapshot.py": "ops",
    "coverage_issue_body.py": "ops",
    "dead_code_pr.py": "ops",
    "doc_consistency_issues.py": "ops",
    "feat_bundle_followup.py": "ops",
    "fetch_github_stats.py": "ops",
    "fetch_github_usage.py": "ops",
    "fetch_pypistats.py": "ops",
    "fp_to_fixture.py": "ops",
    "gh_issue_dedup.py": "ops",
    "kpi_trend_update.py": "ops",
    "kpi_weekly_report.py": "ops",
    "mcp_product_health_server.py": "ops",
    "migrate_ground_truth.py": "ops",
    "normalize_findings.py": "ops",
    "ops_calibration_cycle.py": "ops",
    "ops_outcome_trajectory_cycle.py": "ops",
    "oracle_fp_audit.py": "ops",
    "outcome_first_validation.py": "ops",
    "package_kpis.py": "ops",
    "patch_test_monkeypatches.py": "ops",
    "pattern_rotation.py": "ops",
    "pr_review_loop.py": "ops",
    "profile_drift.py": "ops",
    "quality_scorecard.py": "ops",
    "release_automation.py": "ops",
    "release_readiness.py": "ops",
    "risk_audit_diff.py": "ops",
    "run_single.py": "ops",
    "session_handover.py": "ops",
    "signal_coverage_matrix.py": "ops",
    "task_card.py": "ops",
    "temporal_drift.py": "ops",
    "test_orchestrator.py": "ops",
    "triage_findings.py": "ops",
    "unknown_repo_audit.py": "ops",
    # --- analysis ---
    "ablation_mds_threshold.py": "analysis",
    "diagnose_phases.py": "analysis",
    "experiment_b_bug_correlation.py": "analysis",
    "ground_truth_analysis.py": "analysis",
    "sensitivity_analysis.py": "analysis",
    "study_debt_correlation.py": "analysis",
    "study_rater_agreement.py": "analysis",
    "study_self_analysis_aggregate.py": "analysis",
    "_check_fixtures.py": "analysis",
    "_context_mapping.py": "analysis",
    "_fixture_coverage_matrix.py": "analysis",
    "_gap_analysis.py": "analysis",
    "_gt_analysis.py": "analysis",
    "_precision_detail.py": "analysis",
    "_self_analysis_detail.py": "analysis",
    "_test_map_lookup.py": "analysis",
    "_trend_gaps.py": "analysis",
    # --- experimental ---
    "generate_demo_gif.py": "experimental",
    "make_demo_gif.py": "experimental",
    "make_demo_gifs.py": "experimental",
    "make_launch_film.py": "experimental",
    "make_trailer_cards.py": "experimental",
    "make_trailer_terminal.py": "experimental",
    "make_trailer_v2.py": "experimental",
    "mcp_repro_hang.py": "experimental",
    "_fix_md036.py": "experimental",
    "_fix_md040.py": "experimental",
    "_fix_md040_walk.py": "experimental",
    "_real_repair_after.py": "experimental",
    "_real_repair_analyze.py": "experimental",
    "_repair_repos.py": "experimental",
    "_show_tasks.py": "experimental",
    "_tmp_pfs_catalog.py": "experimental",
    "_tmp_pfs_variants.py": "experimental",
    "_trailer_scenes.py": "experimental",
}

VALID_CATEGORIES = {"gate", "generator", "benchmark", "ops", "analysis", "experimental"}


def _extract_summary(path: Path) -> str:
    """Return the first non-empty line of module docstring, or fallback text."""
    try:
        source = path.read_text(encoding="utf-8")
        module = ast.parse(source)
        docstring = ast.get_docstring(module)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return "No readable module docstring"

    if not docstring:
        return "No module docstring"

    for line in docstring.splitlines():
        text = line.strip()
        if text:
            return text
    return "No module docstring"


def _iter_scripts() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(SCRIPTS_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        entries.append({
            "script": path.name,
            "summary": _extract_summary(path),
            "category": SCRIPT_CATEGORIES.get(path.name, "ops"),
        })
    return entries


def _print_table(entries: list[dict[str, str]]) -> None:
    if not entries:
        print("No scripts found.")
        return

    name_width = max(len(item["script"]) for item in entries)
    name_width = max(name_width, len("Script"))
    cat_width = max(len(item["category"]) for item in entries)
    cat_width = max(cat_width, len("Category"))

    print(f"{'Script'.ljust(name_width)}  {'Category'.ljust(cat_width)}  Summary")
    print(f"{'-' * name_width}  {'-' * cat_width}  {'-' * 60}")
    for item in entries:
        line = (
            f"{item['script'].ljust(name_width)}  "
            f"{item['category'].ljust(cat_width)}  "
            f"{item['summary']}"
        )
        print(line)



def main() -> int:
    parser = argparse.ArgumentParser(description="List scripts with short descriptions.")
    parser.add_argument(
        "--search",
        default="",
        help="Case-insensitive substring filter over script name and summary.",
    )
    parser.add_argument(
        "--category",
        default="",
        choices=sorted(VALID_CATEGORIES) + [""],
        metavar="CATEGORY",
        help=f"Filter by category: {', '.join(sorted(VALID_CATEGORIES))}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of table format.",
    )
    args = parser.parse_args()

    entries = _iter_scripts()
    if args.search:
        needle = args.search.lower()
        entries = [
            item
            for item in entries
            if needle in item["script"].lower() or needle in item["summary"].lower()
        ]
    if args.category:
        entries = [item for item in entries if item["category"] == args.category]

    if args.json:
        print(json.dumps(entries, indent=2, ensure_ascii=True))
    else:
        _print_table(entries)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
