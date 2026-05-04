# scripts/ — Agent-Facing Script Index

This directory contains **142 scripts** organized into six categories.
Agents navigate via `make catalog` or the category filter below — never by browsing raw file listings.

## Quick Navigation

```powershell
# All scripts with category column
make catalog

# Filter by category
make catalog ARGS='--category gate'
make catalog ARGS='--category generator'
make catalog ARGS='--category benchmark'
make catalog ARGS='--category ops'
make catalog ARGS='--category analysis'
make catalog ARGS='--category experimental'

# Search across name + summary
make catalog ARGS='--search evidence'
```

---

## Categories

### gate — Pre-push / CI Validators (25 scripts)

Scripts that block bad commits or detect regressions. Called by CI workflows and Makefile gates.
**Agents: prefer `make gate-check` over calling these directly.**

| Makefile target | Script | Purpose |
|---|---|---|
| `make gate-check COMMIT_TYPE=<typ>` | `gate_check.py` | Proactive pre-push status check |
| `make agent-harness-check` | `check_agent_harness_contract.py` | Harness navigation, audit artifacts, MCP boundaries |
| `make audit-diff` | `risk_audit_diff.py` | Required risk-audit updates for signal/output changes |
| *(pre-push hook)* | `check_release_discipline.py` | CHANGELOG, version, lockfile discipline |
| *(pre-push hook)* | `check_blast_radius_gate.py` | Blast-radius (ADR-087) |
| *(pre-push hook)* | `validate_feature_evidence.py` | Feature-evidence JSON format + tests |
| *(pre-push hook)* | `check_version.py` | pyproject.toml / CHANGELOG / llms.txt version sync |
| *(pre-push hook)* | `check_risk_audit.py` | FMEA/STRIDE/fault-tree update requirement |
| *(pre-push hook)* | `check_schema_compat.py` | JSON Schema contract diff |
| *(CI)* | `check_model_consistency.py` | Signal model ↔ documentation consistency |
| *(CI)* | `check_doc_links.py` | Internal Markdown link validation |
| *(CI)* | `ecosystem_check.py` | Cross-version signal regression |
| *(CI)* | `kpi_trend_gate.py` | KPI trend regression |
| *(CI)* | `perf_gate.py` | Performance regression |
| *(CI)* | `release_risk_gate.py` | Composite release risk |
| *(CI)* | `validate_negative_patterns.py` | Negative-pattern schema compliance |
| *(CI)* | `validate_proposals.py` | CP2 score threshold |
| *(CI)* | `verify_gate_not_bypassed.py` | Approval-gate bypass detector (ADR-089) |
| *(CI)* | `check_negative_patterns.py` | Negative-pattern regression guard |
| *(CI)* | `check_dsol_convergence.py` | CP3 stagnation detection |
| *(CI)* | `check_policy_gate.py` | Policy Gate declaration validator |
| *(CI)* | `check_repo_hygiene.py` | Public-repo hygiene rules |
| *(CI)* | `nudge_gate.py` | Block commit if last nudge demanded REVERT |
| *(CI)* | `ratchet_coverage.py` | Coverage ratchet |
| *(CI)* | `validate_task_spec.py` | TaskSpec YAML/JSON schema |
| *(CI)* | `validate_adr_frontmatter.py` | ADR-087 frontmatter schema |

---

### generator — Deterministic Artifact Generators (15 scripts)

Scripts that produce required artifacts (evidence JSONs, CHANGELOG entries, stubs, schemas).
**Agents: prefer `make` targets — these are the backing implementations.**

| Makefile target | Script | Artifact produced |
|---|---|---|
| `make feat-bundle VERSION=X.Y.Z SLUG=<slug>` | `generate_feature_evidence.py` | `benchmark_results/vX.Y.Z_<slug>_feature_evidence.json` |
| `make changelog-entry COMMIT_TYPE=<typ> MSG='<text>'` | `generate_changelog_entry.py` | CHANGELOG snippet (stdout) |
| `make changelog COMMIT_TYPE=<typ> MSG='<text>'` | `integrate_changelog_entry.py` | Inserts entry into `CHANGELOG.md` |
| `make handover TASK='<desc>'` | `session_handover.py` | `work_artifacts/session_*.md` |
| `make work-index` | `update_work_artifacts_index.py` | `work_artifacts/index.json` |
| *(make check)* | `sync_version.py` | Version-consistency across pyproject/CHANGELOG/llms.txt |
| *(CI)* | `generate_llms_txt.py` | `llms.txt` |
| *(CI)* | `generate_benchmark_baseline.py` | Benchmark baseline JSON |
| *(CI)* | `generate_pr_baseline.py` | PR precision/recall baseline |
| *(CI)* | `generate_repair_coverage_matrix.py` | `benchmark_results/repair_coverage_matrix.json` |
| *(manual)* | `generate_engine_stubs.py` | `src/drift/signals/*.py` re-export stubs |
| *(manual)* | `generate_output_schema.py` | `drift.output.schema.json` |
| *(manual)* | `generate_evidence_schema.py` | `drift.evidence.schema.json` |
| *(manual)* | `generate_annotation_sheet.py` | Blind annotation sheet for inter-rater studies |
| *(manual)* | `build_instruction_registry.py` | Instruction discovery registry |
| *(manual)* | `generate_agent_tasks_evidence.py` | Agent-tasks feature evidence |

---

### benchmark — Evaluation Harnesses (27 scripts)

Controlled benchmarks for precision/recall, mutation detection, agent loop efficiency.
**Agents: use `make replay-benchmark`, `make ab-harness`, or `make repair-eval`.**

| Makefile target | Script | Measures |
|---|---|---|
| `make replay-benchmark` | `replay_benchmark.py` | Historical drift score correlation |
| `make ab-harness` | `ab_harness.py` | A/B agent loop efficiency |
| `make repair-eval` | `repair_eval.py` | Repair side-effects and success rate |
| *(manual)* | `mutation_benchmark.py` / `_mutation_benchmark.py` | Mutation detection recall |
| *(manual)* | `benchmark_agent_loop.py` / `run_agent_loop_benchmark.py` | Agent loop E2E efficiency |
| *(manual)* | `benchmark_mcp_perf.py` | MCP tool latency |
| *(manual)* | `benchmark_cross_version.py` | Cross-version signal stability |
| *(manual)* | `benchmark_repos.py` / `benchmark.py` | Real-world corpus scan |
| *(manual)* | `defect_corpus_benchmark.py` | Defect corpus recall |
| *(manual)* | `copilot_behavioral_benchmark.py` | Copilot prompt-pair evaluation |
| *(manual)* | `copilot_context_benchmark.py` | Copilot context coverage |
| *(manual)* | `corpus_scan.py` | Batch oracle corpus scan |
| *(manual)* | `repair_benchmark.py` | Repair benchmark |
| *(manual)* | `adversarial_brief_audit.py` | Adversarial brief audit (H5) |
| *(manual)* | `evaluate_benchmark.py` | Per-signal precision/recall from results |
| *(manual)* | `mirror_ab_study.py` / `brief_ab_study.py` | Mirror-mode / brief A/B study |
| *(manual)* | `holdout_validation.py` | Leave-one-out cross-validation |
| *(manual)* | `mutation_gap_report.py` | Mutation gap report (H3) |
| *(manual)* | `signal_mutation_test.py` | Cross-platform signal mutation test |
| *(internal)* | `_bench_utils.py` | Shared benchmark utilities |
| *(internal)* | `_mirror_experiment.py` | Mirror-mode experiment helper |

---

### ops — Operational Tools (36 scripts)

Release management, KPI tracking, session tools, triage, profiling.
**Agents: use `make` targets where available.**

| Makefile target | Script | Purpose |
|---|---|---|
| `make task-card TYPE=<typ> TASK='<desc>'` | `task_card.py` | Compact task kickoff card |
| `make catalog [ARGS='...']` | `catalog.py` | Script index with category filter |
| `make kpi-update` | `kpi_trend_update.py` | Append KPI snapshot to trend JSONL |
| `make kpi-report` | `kpi_weekly_report.py` | Weekly KPI report |
| *(CI)* | `ops_calibration_cycle.py` | Repeatable calibration cycle |
| *(CI)* | `quality_scorecard.py` | ISO/IEC 25010 quality scorecard |
| *(CI)* | `oracle_fp_audit.py` | FP audit on curated high-FP repos |
| *(CI)* | `pattern_rotation.py` | Auto-generate negative patterns |
| *(CI)* | `collect_kpi_snapshot.py` | KPI snapshot collection |
| *(CI)* | `fetch_github_usage.py` + `fetch_pypistats.py` | Usage stats fetch |
| *(CI)* | `package_kpis.py` | Monthly KPI set |
| *(CI)* | `coverage_issue_body.py` | Coverage regression detector |
| *(CI)* | `ci_drift_trend_alert.py` + `ci_fp_threshold_alert.py` | CI alert triggers |
| *(CI)* | `doc_consistency_issues.py` | Doc-consistency issue creation |
| *(CI)* | `dead_code_pr.py` | Dead code PR helper |
| *(CI)* | `outcome_first_validation.py` | 14-day outcome validation runner |
| *(manual)* | `release_automation.py` | Full release automation |
| *(manual)* | `release_readiness.py` | Release readiness aggregator |
| *(manual)* | `mcp_product_health_server.py` | Standalone MCP product health server |
| *(manual)* | `agent_repro_bundle.py` | Compact repro bundle for failing agents |
| *(manual)* | `triage_findings.py` | Interactive findings triage |
| *(manual)* | `normalize_findings.py` | Normalize review findings |
| *(manual)* | `fp_to_fixture.py` | Convert FP findings to CONFOUNDER fixtures |
| *(manual)* | `migrate_ground_truth.py` | Ground truth JSON migration |
| *(manual)* | `profile_drift.py` | Profile drift analyze |
| *(manual)* | `run_single.py` | Single-repo scan + compact output |
| *(manual)* | `temporal_drift.py` | Temporal score timeline |
| *(manual)* | `signal_coverage_matrix.py` | Signal coverage matrix |
| *(manual)* | `ops_outcome_trajectory_cycle.py` | Retrospective outcome trajectory |
| *(manual)* | `pr_review_loop.py` | PR-review loop CLI wrapper |
| *(manual)* | `test_orchestrator.py` | Risk-based test orchestrator |
| *(manual)* | `patch_test_monkeypatches.py` | Bulk-patch test monkeypatches for ADR-100 |
| *(manual)* | `gh_issue_dedup.py` | Opt-in BLOCK-finding issue dedup |
| *(manual)* | `fetch_github_stats.py` | GitHub REST stats |
| *(manual)* | `unknown_repo_audit.py` | Precision audit on unknown repos |
| *(manual)* | `pr_review_loop.py` | PR-review loop CLI |

---

### analysis — Research and Studies (17 scripts)

One-off analyses, correlation studies, precision breakdowns. Mainly human-readable output.

| Script | Purpose |
|---|---|
| `sensitivity_analysis.py` | Scoring-weight sensitivity |
| `ground_truth_analysis.py` | Ground-truth finding classification |
| `study_debt_correlation.py` | Drift score ↔ debt correlation |
| `study_rater_agreement.py` | Inter-rater agreement (Fleiss' kappa) |
| `study_self_analysis_aggregate.py` | Self-analysis community aggregation |
| `ablation_mds_threshold.py` | MDS threshold ablation |
| `diagnose_phases.py` | Phase-level latency diagnosis |
| `experiment_b_bug_correlation.py` | Drift ↔ bug correlation (precision 59%) |
| `holdout_validation.py` | Leave-one-out cross-validation |
| `_gap_analysis.py` | Benchmark gap analysis |
| `_gt_analysis.py` | Ground truth fixture coverage per signal |
| `_fixture_coverage_matrix.py` | Fixture coverage matrix |
| `_context_mapping.py` | Task-type to context-path mapping |
| `_check_fixtures.py` | Fixture consistency check |
| `_precision_detail.py` | Per-signal precision breakdown |
| `_self_analysis_detail.py` | Self-analysis gap identification |
| `_trend_gaps.py` | Trend gap identification |
| `_test_map_lookup.py` | Source-file → relevant-test lookup |

---

### experimental — Temporary / Media / One-offs (18 scripts)

Experimental code, trailer/demo generation, repro helpers. Not part of CI or standard workflows.
**Do not reference these in new CI gates or Makefile targets.**

| Script | Purpose |
|---|---|
| `_tmp_pfs_catalog.py` / `_tmp_pfs_variants.py` | Temporary PFS debugging helpers |
| `mcp_repro_hang.py` | MCP event-loop hang repro |
| `make_trailer_v2.py` / `make_trailer_cards.py` / `make_trailer_terminal.py` | Trailer video generation |
| `make_launch_film.py` | Launch film render |
| `make_demo_gif.py` / `make_demo_gifs.py` / `generate_demo_gif.py` | Demo GIF generation |
| `_fix_md036.py` / `_fix_md040.py` / `_fix_md040_walk.py` | One-shot Markdown fixers |
| `_real_repair_after.py` / `_real_repair_analyze.py` / `_repair_repos.py` | Real-repo repair experiments |
| `_show_tasks.py` | Show repair tasks from analysis |
| `_trailer_scenes.py` | Curated trailer output scenes |

---

## Adding a New Script

1. Add the script to `scripts/`.
2. Add a module docstring (first non-empty line becomes the catalog summary).
3. Register it in `SCRIPT_CATEGORIES` in `catalog.py` with the correct category.
4. If it needs a `make` target, add it to `Makefile`.
5. If it's a CI gate, add the workflow reference and update the gate table above.

## Subdirectory Migration

The current flat layout is intentional — 35 scripts are hardcoded in CI workflow YAMLs.
A subdirectory migration (`gates/`, `generators/`, `benchmarks/`, `ops/`) requires atomic
updates to all workflow files and the Makefile. This is tracked as a separate issue.
Until then, use `make catalog --category <cat>` for filtered views.
