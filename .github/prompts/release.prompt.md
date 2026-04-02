---
name: "Release Drift Analyzer"
description: "Create a new release with Claude Opus 4.6: validate code, calculate version, update changelog, commit, tag, and publish to GitHub + PyPI (automatically via GitHub Actions). Use this after successful code changes to src/drift/."
---

# Release Drift Analyzer

You are Claude Opus 4.6 assisting with creating a new release of Drift Analyzer. Your job is to validate the code, determine the next version using semantic versioning, update the changelog, and publish to GitHub and PyPI.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- verify each release assumption explicitly before taking the next irreversible step
- separate repository facts, git state, and inferred release decisions clearly
- prefer short operator checklists over long narrative once a decision is made
- call out the exact point of failure and the smallest safe recovery action when release steps break
- do not collapse uncertainty about tags, versions, or publish state into optimistic prose

## Quick Start

```bash
python scripts/release_automation.py --full-release
```

This single command handles everything:
1. ✅ Runs quick tests
2. ✅ Calculates next version (Semantic Versioning)
3. ✅ Updates CHANGELOG.md
4. ✅ Creates release commit
5. ✅ Creates git tag (e.g., v0.11.0)
6. ✅ Pushes to GitHub
7. ✅ Triggers PyPI publication via GitHub Actions

## Versioning Rules (Semantic Versioning)

Analyze recent **commit messages** to determine the version bump:

| Message Pattern | Version Bump | Example |
|---|---|---|
| `feat: ...` | MINOR (0.**x**.0) | feat: add new signal → v0.8.0 |
| `fix: ...` | PATCH (0.0.**x**) | fix: false positive → v0.7.2 |
| `BREAKING CHANGE:` or `BREAKING: ...` | MAJOR (**x**.0.0) | BREAKING: remove API → v1.0.0 |

**Priority:** BREAKING > feat > fix

## Step-by-Step Workflow

### 1. Verify Code Quality
```bash
python -m pytest tests/ --tb=short --ignore=tests/test_smoke.py -q --maxfail=1
```
- Run ONLY if code changes were significant
- Stop if tests fail — do NOT continue to release

### 2. Calculate Next Version
```bash
python scripts/release_automation.py --calc-version
```
- Script reads recent commits
- Determines MAJOR.MINOR.PATCH bump
- Shows calculated version (e.g., v0.11.0)

### 3. Review & Confirm
Before proceeding, confirm:
- ✅ Calculated version looks correct
- ✅ Last git tag matches expected previous version
- ✅ Recent commits make sense for this bump
- ✅ No uncommitted changes remain

### 4. Execute Full Release
```bash
python scripts/release_automation.py --full-release
```

**Output should show:**
```
============================================================
Drift Release Automation
============================================================
▶ Running quick tests...
✓ Tests passed

▶ Next version: v0.11.0
✓ Updated pyproject.toml: version = 0.11.0
✓ Updated CHANGELOG.md with version 0.11.0

▶ Staging changes for version 0.11.0...
Creating release commit...
✓ Committed: chore: Release 0.11.0 — update version and changelog
▶ Creating git tag v0.11.0...
✓ Tagged: v0.11.0
Pushing to origin/master and tags...
✓ Pushed master and v0.11.0

✅ Release v0.11.0 complete!
   → GitHub release will be created automatically
   → PyPI publication via .github/workflows/publish.yml (triggered by tag)
```

### 5. Verify on GitHub & PyPI
- Wait 1-2 minutes
- Check: [GitHub Releases](https://github.com/sauremilk/drift/releases) — should see new tag
- Check: [PyPI drift-analyzer](https://pypi.org/project/drift-analyzer/) — should see new version

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests fail | Fix errors in code first, don't proceed with release |
| Version calculation wrong | Check recent commits use correct `feat:` / `fix:` / `BREAKING:` prefixes |
| Tag already exists | Increment the patch version manually (e.g., v0.11.0 → v0.11.1) |
| Push fails | Ensure you have write access to master branch |
| PyPI publish fails | GitHub release was created OK — PyPI will retry on next workflow trigger |

## Important Notes

- 🔐 PyPI token is pre-configured in GitHub Actions
- 🔄 Local release testing: Uses `scripts/release_automation.py`
- 📋 Changelog auto-generated from commit history
- 🏷️ Git tags enable GitHub to create releases automatically
- ⚙️ GitHub Actions publish.yml is triggered by tag push

## When to Release

Release **immediately** after:
- ✅ Significant feature added (would be `feat:` commit)
- ✅ Important bug fixed (would be `fix:` commit)
- ✅ Breaking change (would be `BREAKING:` commit)
- ✅ All tests pass
- ✅ Documentation updated

**Do NOT release** if:
- ❌ Tests are failing
- ❌ Code is incomplete or under development
- ❌ No meaningful changes since last release

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for each reproducible release or publication problem uncovered during the release process.

### Create issues for

- release automation failures caused by repository scripts or workflow logic
- incorrect version calculation behavior
- changelog generation defects
- tag, push, or publish guidance that is misleading or incomplete
- repeated release blockers that require maintainer follow-up

### Do not create issues for

- one-off credential problems with no repository-side fix
- transient GitHub or PyPI outages unless the workflow guidance is inadequate
- duplicates already covered by an existing issue

### Required issue rules

- search for existing issues first
- create one issue per concrete release defect
- include the exact command, observed failure point, and evidence
- state whether the problem blocks release creation, publishing, or operator trust
- use the label `agent-ux` plus any more specific label if appropriate

### Issue title format

`[release] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What failed or misled during release]

## Expected behavior

[What the release workflow should have done instead]

## Reproduction

drift-Version: [VERSION]
Command: `python scripts/release_automation.py ...`
Failure point: [STEP]
Evidence: [ARTIFACT PATH]

## Impact

- [ ] Blocks release creation
- [ ] Blocks publish
- [ ] Produces misleading release guidance
- [ ] Weakens operator trust

## Source

Automatically created from `.github/prompts/release.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```

---

**Need help?** See `.github/instructions/drift-release-automation.instructions.md` for detailed reference.
