## Summary

Describe the problem and fix in 2–5 bullets:

- Problem:
- Why it matters:
- What changed:
- What did NOT change (scope boundary):

## Linked Issue / PR

- Closes #
- Related #

## Type of change (select all that apply)

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor (required for the fix)
- [ ] Documentation
- [ ] Test-only change
- [ ] CI/Build change

## First contribution?

- [ ] This is my first contribution to drift

<!-- First-time contributors: don't worry about getting everything perfect.
     Maintainers will guide you through the review process. -->

## Policy criterion served

<!-- Which quality goal does this PR advance? Check at least one. -->

- [ ] Credibility (reproducibility, determinism)
- [ ] Signal precision (fewer false positives/negatives)
- [ ] Finding clarity (better explanations, actionable next steps)
- [ ] Adoptability (easier setup, onboarding, docs)
- [ ] Trend capability (temporal analysis, delta tracking)
- [ ] None of the above — explain why this is still valuable:

## Root Cause (if applicable)

For bug fixes or regressions, explain **why** this happened, not just what changed.
Otherwise write `N/A`. If the cause is unclear, write `Unknown`.

- Root cause:
- Missing detection / guardrail:
- Contributing context (if known):

## Regression Test Plan (if applicable)

For bug fixes or regressions, name the smallest reliable test coverage that
should catch this. Otherwise write `N/A`.

- Coverage level that should have caught this:
  - [ ] Unit test
  - [ ] Integration test
  - [ ] Existing coverage already sufficient
- Target test or file:
- Scenario the test should lock in:
- If no new test is added, why not:

## User-visible / Behavior Changes

List user-visible changes (including defaults, config keys, CLI flags, output format).
If none, write `None`.

## Diagram (if applicable)

For non-trivial logic flows or output format changes, include a small ASCII diagram.
Otherwise write `N/A`.

```
Before:
[input] -> [old behavior]

After:
[input] -> [new behavior] -> [result]
```

## Security Impact (required)

- New permissions / capabilities? (`Yes/No`)
- Input validation surface changed? (`Yes/No`)
- File system or subprocess access changed? (`Yes/No`)
- Secrets / tokens handling changed? (`Yes/No`)
- If any `Yes`, explain risk + mitigation:

## Repro + Verification

### Environment

- OS:
- Python version:
- drift-analyzer version:
- Relevant config (redacted):

### Steps

1.
2.
3.

### Expected

-

### Actual

-

## Evidence

Attach at least one of:

- Failing test / log before + passing after
- `drift analyze` output diff
- Benchmark / precision-recall numbers
- Screenshot (for docs or DX changes)

## Human Verification (required)

What you personally verified (not just CI), and how:

- Verified scenarios:
- Edge cases checked:
- What you did not verify:

## Review Conversations

I replied to or resolved every bot review conversation I addressed in this PR.
I left unresolved only conversations that still need reviewer judgment.

## Compatibility / Migration

- Backward compatible? (`Yes/No`)
- Config / env changes? (`Yes/No`)
- Migration needed? (`Yes/No`)
- If yes, exact upgrade steps:

## Release notes label (required)

<!-- Add exactly one release:* label to this PR so Release Drafter can categorize it. -->

- [ ] `release:feature`
- [ ] `release:fix`
- [ ] `release:maintenance`
- [ ] `release:docs`
- [ ] `release:skip` (internal-only, should not appear in release notes)

## Validation

- [ ] `pytest` passes locally
- [ ] `ruff check src/ tests/` passes locally
- [ ] `mypy src/drift` passes locally
- [ ] `drift self` delta checked (target: <= +0.010)
- [ ] Added/updated tests for behavioral changes

## Empirical evidence (required for new features)

- [ ] This PR introduces no new feature (skip section)
- [ ] OR: empirical artifact added/updated in `benchmark_results/` or `audit_results/`
- [ ] OR: feature has benchmark/validation output attached in PR description

Evidence summary (required when feature is introduced):

- Scope / dataset:
- Baseline result:
- New result:
- Reproduction command:
- Interpretation (precision/noise/runtime impact):

## Checklist

- [ ] PR is focused on one concern
- [ ] Public docs updated (README/docs-site) if needed
- [ ] Changelog entry added if user-visible
- [ ] If version/changelog changed: top release entry still fits one short summary plus at most 5 curated bullets
- [ ] No unrelated files included

## Risk Audit (POLICY §18 — required for signal/architecture changes)

- [ ] This PR does **not** touch `src/drift/signals/`, `src/drift/ingestion/`, or `src/drift/output/` (skip section)
- [ ] OR: `audit_results/fmea_matrix.md` updated (FP + FN entry for affected signal)
- [ ] OR: `audit_results/stride_threat_model.md` updated (new/changed trust boundary)
- [ ] OR: `audit_results/fault_trees.md` reviewed (FT-1/FT-2/FT-3 paths checked)
- [ ] OR: `audit_results/risk_register.md` updated (new risk entry or metric update)
- [ ] All four audit artifacts still exist and are not deleted

## Risks and Mitigations

List only real risks for this PR. If none, write `None`.

- Risk:
  - Mitigation:

## Notes for reviewers

<!-- Anything that needs special attention during review -->
