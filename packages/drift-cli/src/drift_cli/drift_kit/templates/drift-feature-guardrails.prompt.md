---
name: drift-feature-guardrails
description: >
  Use BEFORE implementing a new feature to assess architectural risk. Reads
  `.vscode/drift-session.json` (if available) and identifies which drift signals
  the planned feature is likely to worsen. Returns a risk assessment, targeted
  guardrails, and questions to ask before writing code.
---

# Drift: Feature Guardrails

Assess the architectural risk of a planned feature before any code is written.
Use this to prevent drift-score regressions and catch structural issues early —
before they are baked into the implementation.

## Context

Read `.vscode/drift-session.json` if it exists.
If the file does not exist: skip the personalized risk section and proceed with
generic signal guidance based on the user's feature description. Recommend running
`drift analyze --repo . --exit-zero` afterwards to establish a baseline.
If `analyzed_at` is older than 24 hours: note the staleness and proceed with the
available data. Do not block.

## Workflow

1. **Understand the planned feature**: ask the user to describe in 1-3 sentences
   what the feature adds, changes, or removes. If they already described it in
   the current prompt, use that description.

2. **Map feature to risk signals**:
   Identify which of the following signal types the feature is likely to trigger
   or worsen based on the description:
   - **PFS** (Pattern Fragmentation): new code that introduces a second way of
     doing something already done consistently elsewhere.
   - **AVS** (Architecture Violation): code that crosses module boundaries or
     introduces cross-layer dependencies.
   - **MDS** (Mutant Duplicates): new logic that replicates existing logic with
     minor variations.
   - **EDS** (Explainability Deficit): new functions or classes without clear
     single responsibility.
   - **DCA** (Dead Code Accumulation): new exports that may not be consumed.

3. **Personalize with session data** (if `.vscode/drift-session.json` exists):
   Cross-reference the above with the `top_findings` in the session file.
   If the planned feature touches files already flagged, call that out explicitly.

4. **Produce the risk assessment**:
   - **Risk level**: low / medium / high (based on signal overlap and affected file count).
   - **Most likely signals**: list the 1-3 signals most likely to be triggered.
   - **Guardrails**: 2-5 concrete rules to follow during implementation to avoid
     worsening those signals (e.g., "extract shared logic into an existing utility
     module rather than duplicating it").
   - **Questions to answer first**: 2-3 design questions that, if answered before
     coding, reduce the risk (e.g., "Does an existing module already own this
     responsibility?").

5. **Recommend a post-implementation check**:
   Remind the user to run `drift analyze --repo . --exit-zero` after the feature
   lands and compare the score to the pre-feature baseline.

## Output

- **Risk level** (low / medium / high) with one-sentence justification.
- **Guardrail list** (2-5 bullet points).
- **Questions to answer first** (2-3 bullet points).
- _(Optional)_ Affected files from `top_findings` that overlap with the feature scope.

## Next Step

After completing this workflow, continue with:
- **[/drift-fix-plan]** — review the current finding backlog before starting.
- **[/drift-auto-fix-loop]** — apply outstanding fixes before adding new complexity.
