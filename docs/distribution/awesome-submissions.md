# Awesome Submissions

This document contains ready-to-submit entries for discovery lists where developers actively evaluate tools.

## Goal

Increase top-of-funnel discovery for drift via curated lists with high evaluator intent.

## Target 1: awesome-python

- Repository: https://github.com/vinta/awesome-python
- Section: Code Analysis
- Suggested entry:

```markdown
* [drift](https://github.com/mick-gsk/drift) - Deterministic architecture erosion detection for AI-accelerated Python codebases with actionable findings and CI integration.
```

- Suggested PR title:

```text
Add drift to Code Analysis section
```

- Suggested PR body:

```markdown
## What this adds
Adds [drift](https://github.com/mick-gsk/drift), an open-source static analyzer focused on architectural coherence in AI-accelerated Python repositories.

## Why it belongs
- Deterministic analysis (no LLM dependency in the detection pipeline)
- Practical CI/CD integration with report-only and gated rollout
- Actionable findings for pattern fragmentation, architecture violations, and near-duplicate logic

If preferred, I can shorten the one-line description further.
```

## Target 2: awesome-static-analysis

- Repository: https://github.com/analysis-tools-dev/static-analysis
- Expected file: data/tools/python.yml
- Suggested YAML entry:

```yaml
- name: drift
  categories: [code-quality, architecture]
  languages: [python]
  description: >
    Deterministic architecture erosion detection for AI-accelerated Python codebases,
    with actionable findings for pattern fragmentation, architecture violations,
    near-duplicate logic, explainability deficits, and temporal instability.
  homepage: https://github.com/mick-gsk/drift
  license: MIT
```

- Suggested PR title:

```text
Add drift: deterministic architectural drift analysis for Python
```

- Suggested PR body:

```markdown
## What this adds
Adds `drift` to the Python tooling list.

## Why this tool is relevant
- Targets architectural erosion, not only syntax/style issues
- Deterministic and reproducible output
- Supports terminal, JSON, and SARIF output for team workflows

Homepage: https://github.com/mick-gsk/drift
```

## Submission Checklist

- Verify section placement matches maintainer guidelines.
- Keep one-liner neutral and non-promotional.
- Ensure links resolve and README headline matches the description.
- Keep scope clear: architecture/coherence analysis, not bug detection.
- Merge one list at a time to simplify maintainer review.

## Tracking

Record opened PR links here once submitted:

- awesome-python PR:
- awesome-static-analysis PR:
