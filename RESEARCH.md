# Open Research Questions

This document tracks hypotheses that drift's current evidence base cannot yet answer.
Each hypothesis is falsifiable, cites the current state of evidence, and proposes a concrete validation approach.

Contributions — especially independent replications — are welcome. See [Contributing](CONTRIBUTING.md).

---

## H1 — External validity of the mutation benchmark

**Hypothesis:** The 25 mutation patterns in [mutation_benchmark.json](benchmark_results/mutation_benchmark.json) are representative of real-world structural drift, not just synthetic edge cases.

**Current evidence:** 100 % recall on the mutation suite, but all patterns were authored by the maintainer. The recall figure demonstrates detection coverage, not ecological validity.

**Validation approach:** Collect naturally occurring drift examples from community-reported issues and open-source codebases. Compare the naturally occurring pattern distribution against the synthetic suite. If > 20 % of real-world patterns have no mutation counterpart, the suite requires expansion.

**Status:** Open — no independent replication exists.

**Instrument:** `scripts/generate_annotation_sheet.py --compare rater1.json rater2.json` computes Cohen's κ over blind annotations. Gate: κ ≥ 0.60 for sufficient inter-rater agreement. Output: `benchmark_results/annotation_agreement.json`.

---

## H2 — Construct validity of "structural drift"

**Hypothesis:** The construct "structural drift" as measured by drift's 24 signals corresponds to a real, cohesive phenomenon rather than a loose bundle of heterogeneous code-quality metrics.

**Current evidence:** Signals were designed around a shared thesis (cross-file structural erosion), but no factor analysis or inter-signal correlation study has been conducted. Some signals measure overlapping phenomena (MDS/PFS for code similarity, CCC/TVS for change history).

**Validation approach:** Run drift on 50+ diverse repositories. Perform exploratory factor analysis on signal scores. If signals cluster into ≤ 3 coherent factors, the construct has good internal structure. If they scatter into > 6 uncorrelated factors, the composite score conflates unrelated dimensions.

**Status:** Open — requires a large-scale corpus study.

**Instrument:** `scripts/corpus_scan.py` batch-scans the 10 oracle repos, builds a signal score correlation matrix, and performs PCA via power iteration. Gate: ≤ 3 components explain ≥ 70 % of variance. Output: `benchmark_results/corpus_scan.json`.

---

## H3 — Causal link between drift score and maintenance outcomes

**Hypothesis:** A higher drift score predicts higher future maintenance effort (bug density, mean time to merge, contributor churn).

**Current evidence:** The current benchmark measures detection quality (precision/recall), not predictive validity. No longitudinal study has been conducted. The Kendall's τ weight derivation (5 repos, single rater) establishes rank correlation between signal scores and expert judgment, but not a causal or predictive relationship.

**Validation approach:** Select 30+ repositories with public issue trackers. Compute drift scores at monthly intervals over 12 months. Correlate score trajectories with bug-fix commit density, open-issue count, and contributor activity. Control for repo size, language, and team size.

**Status:** Open — requires longitudinal data collection.

**Instrument:** `scripts/mutation_gap_report.py` clusters real-world findings from `*_full.json` evidence files and compares against the 25-pattern mutation suite. Gate: coverage ≥ 80 %. Output: `benchmark_results/mutation_gap_report.json`.

---

## H4 — Agent guardrail compliance rate

**Hypothesis:** Coding agents that receive `drift brief` constraints produce fewer structural violations than agents working without constraints.

**Current evidence:** The [agent loop benchmark](benchmark_results/agent_loop_benchmark.json) measures whether brief output is syntactically valid and coverage-complete. It does not measure whether agents actually follow the constraints or whether compliance correlates with better code quality. A first observational data point exists: a [Copilot Autopilot live run](demos/copilot-autopilot/) on openclaw/openclaw produced a score delta of 0.495→0.506 with 4 findings resolved, but also introduced 10 new findings — this is a single uncontrolled session, not a controlled experiment.

**Validation approach:** Run controlled A/B experiments: give an agent 20 coding tasks with and without `drift brief` constraints. Measure violation count, task completion rate, and human-assessed code quality on both groups. If the constraint group shows ≥ 30 % fewer violations at comparable task completion, the guardrail mechanism is effective.

**Status:** Open — requires controlled agent experiments. One observational session available.

**Instrument:** `scripts/brief_ab_study.py run-mock` generates deterministic mock agent diffs without an API key (seed-based). Full pipeline: `generate-prompts → run-mock → evaluate → stats → assemble`. Output: `benchmark_results/brief_ab_study.json`.

---

## H5 — Falsifiability of "drift brief" effectiveness claims

**Hypothesis:** It is possible to construct a codebase where `drift brief` constraints actively mislead an agent (i.e., compliance with the constraints produces worse code than ignoring them).

**Current evidence:** Three verified adversarial scenarios from a real 1730-file Python production monorepo (Fortnite AI Coach, drift v2.44.0, `vibe-coding` profile) confirm the hypothesis (reported in [Issue #543](https://github.com/mick-gsk/drift/issues/543)):

- **Scenario A — deferred-pod PFS constraint (Issue #543):** `drift_brief` returned a PFS consolidation constraint ("125 api_endpoint variants found — adopt canonical pattern from `admin.py`") for a task targeting a router file explicitly marked `deferred:` in `drift.yaml` until 2026-Q3/Q4 (DEC-MVP-001 / MVP Scope Guard). Following the constraint would have imported active-pod code into a deferred pod, creating an unwanted cross-pod dependency invisible to tests. Root cause: `drift_brief` has no awareness that the task's target file is covered by a `deferred:` pattern and treats all files in the scan path as equally applicable. Proposed mitigation: check target file against `deferred:` patterns and skip or annotate constraints accordingly.

- **Scenario B — BIFL-isolation MDS constraint (Issue #543):** MDS fired on `hitmarker_detector.py` ↔ `storm_surge_detector.py` (and other pairs in `src/perception/`) because they share `__init__`, `detect(frame)`, and `reset()` structure. The brief recommended extracting a common `DetectorBase` class. However, these detectors follow the BIFL (Beyond-If-Then Learning) architecture (research principle P15): each is intentionally self-contained with independently tuned Z-score baselines and learned parameters. Introducing a shared base class would either expose cross-detector mutable state or provide no real benefit. In the 10 Hz real-time pipeline this risks cross-detector state contamination between frames. The signals are technically accurate but the brief's recommended fix is architecturally wrong. Missing capability: a `deliberate_isolation:` config key (analogous to `deferred:`) to declare that MDS findings in a file group are expected and should not generate consolidation constraints.

- **Scenario C — hot-path EDS/GCD constraint (Issue #543):** EDS and GCD fired on trivially obvious guard clauses in `src/core/pipeline/loop.py` (the 10 Hz main loop): `if frame is None: return`. The brief instructed: "Add docstrings or comments to guard clauses before proceeding." Adding docstrings to every 3-word guard clause provides zero runtime benefit and measurable maintenance overhead per refactor. The team operates under research principle P20 (CPU <1%, Render <16ms) with an explicit convention that guard clauses in sub-16ms pipeline code are intentionally comment-free. Proposed mitigation: `min_guard_complexity` threshold in EDS config, or a `drift:context="hot-path"` annotation to suppress EDS/GCD for performance-critical files.

**Common thread across all three scenarios:** `drift_brief` generates constraints from signal findings without checking whether the architectural context (deferred pod, intentional isolation, hot-path convention) makes the constraint applicable. This is the highest-risk failure mode for a guardrail tool: **false confidence** that following the brief is always architecturally safe.

The earlier observational data point (Copilot Autopilot live run — resolved 4 findings but introduced 10 new ones) remains additional supporting evidence.

**Validation approach:** Design 10 pathological codebase configurations where drift signals are technically accurate but the recommended constraints would be counterproductive (e.g., intentional code duplication for isolation, deprecated-looking modules that are actively maintained). Run agents with and without brief constraints. If agents score worse with constraints in ≥ 3/10 scenarios, the brief mechanism needs scope guards. The three production scenarios from Issue #543 provide an immediately usable 3-scenario benchmark skeleton for the A/B study proposed in H4.

**Status:** Partially confirmed — 3 verified production adversarial scenarios available (Issue #543). Controlled agent A/B benchmark pending.

**Instrument:** `scripts/adversarial_brief_audit.py` runs `drift brief` on 5 adversarial fixtures (`benchmarks/gauntlet/scenarios/adversarial/`) and checks whether output recommends harmful actions. Gate: harmful constraints in ≥ 3/5 fixtures → scope guards needed. Output: `benchmark_results/adversarial_brief_audit.json`.

---

## How to contribute

If you have data, replications, or counterexamples relevant to any hypothesis:

1. Open a [discussion](https://github.com/mick-gsk/drift/discussions) referencing the hypothesis number (e.g., "H2 — factor analysis on 60 repos").
2. Attach raw data or link to a reproducible notebook.
3. The maintainer will update this document with new evidence and adjust the status.

Independent replications — even small ones — are the most valuable contribution to drift's credibility.
