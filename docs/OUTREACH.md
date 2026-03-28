# Outreach Texte

Fertige Texte zum Copy-Paste für externe Plattformen.
Reihenfolge = empfohlene Priorität.

## Naming + Claim Guardrails

- Repo: `sauremilk/drift`
- Package: `drift-analyzer`
- Command: `drift`
- Safe signal claim: 15 scoring signals, all active in the current model (6 core + 9 promoted/new, auto-calibrated at runtime).
- Safe rollout claim: start report-only in CI, then tighten to `high` only after reviewing real findings.

---

## 1. Show HN (Hacker News)

**Titel:**

```
Show HN: Drift – Deterministic architectural drift detection for AI-accelerated Python codebases
```

**Text (im Kommentarfeld):**

```
I built a static analyzer for deterministic architectural drift detection in
AI-accelerated Python codebases.

The problem: Copilot, Cursor, and ChatGPT optimize for the prompt context, not
the codebase context. The result is code that works but doesn't fit — error
handling fragments across 4 different patterns, import boundaries erode, and
near-identical functions accumulate with subtle differences.

Drift doesn't detect bugs. It detects the loss of design intent.

It runs 15 scoring signals today — 6 core signals plus 9 promoted consistency
and contract signals, all contributing to the composite score:
- Pattern Fragmentation: same pattern implemented N different ways in one module
- Architecture Violations: imports crossing layer boundaries (DB → API, etc.)
- Mutant Duplicates: near-identical functions that diverged after copy-paste
- Explainability Deficit: complex functions without docs/types/tests
- Temporal Volatility: files changed by too many hands too fast
- System Misalignment: recently introduced patterns foreign to their module

All signals are deterministic, LLM-free, fast. Uses Python's built-in `ast`
module, so there are zero dependencies on ML infrastructure.

Repo: sauremilk/drift
Package: drift-analyzer
CLI:  drift analyze --repo .
CI:   uses: sauremilk/drift@v1  (GitHub Action, report-only by default)
Hook: pre-commit hook available

Repo: https://github.com/sauremilk/drift
```

**Posting-Tipps:**

- Bester Zeitpunkt: Montag–Dienstag, 9–11 Uhr US Eastern (= 15–17 Uhr DE)
- URL: https://news.ycombinator.com/submitlink?u=https://github.com/sauremilk/drift

---

## 2. Reddit r/Python

**Titel:**

```
I built drift – deterministic architectural drift detection for AI-accelerated Python repos
```

**Text:**

```
TL;DR: `pip install -q drift-analyzer && drift analyze --repo .`

Copilot and Cursor write code that solves local tasks correctly but weakens
global design. Drift detects that architectural drift with 15 scoring signals
covering pattern, architecture, and consistency dimensions:

1. Pattern Fragmentation – same thing done N ways in one module
2. Architecture Violations – wrong-direction imports
3. Mutant Duplicates – near-identical functions (copy-paste-then-modify)
4. Explainability Deficit – complex functions without docs or types
5. Temporal Volatility – files changed by too many authors too fast
6. System Misalignment – patterns foreign to their target module

No LLMs in the detection pipeline. Pure AST analysis + statistics.
Outputs: rich terminal dashboard, JSON, or SARIF for GitHub Code Scanning.

GitHub: https://github.com/sauremilk/drift
```

**Subreddits (alle posten):**

- r/Python
- r/programming
- r/softwarearchitecture
- r/devops

---

## 3. awesome-static-analysis PR

**Repo:** https://github.com/analysis-tools-dev/static-analysis/pulls

**Datei:** `data/tools/python.yml` (oder ähnlich, je nach Repo-Struktur)

**Eintrag:**

```yaml
- name: drift
  categories: [code-quality, architecture]
  languages: [python]
  description: >
    Deterministic architectural drift detection for AI-accelerated Python codebases.
    Measures pattern fragmentation, architecture violations, mutant duplicates,
    explainability deficit, temporal volatility, and system misalignment.
  homepage: https://github.com/sauremilk/drift
  license: MIT
```

**PR-Titel:** `Add drift – architectural drift detector for AI-accelerated Python repos`

---

## 4. awesome-python PR

**Repo:** https://github.com/vinta/awesome-python/pulls

**Abschnitt:** `Code Analysis`

**Eintrag:**

```
* [drift](https://github.com/sauremilk/drift) - Deterministic architectural drift detection for AI-accelerated Python codebases.
```

**PR-Titel:** `Add drift to Code Analysis section`

---

## 5. Reddit r/ExperiencedDevs

**Titel:**

```
How do you detect architectural drift in AI-accelerated codebases?
```

**Text:**

```
I've been working on a problem that I think many experienced teams are quietly
dealing with: AI coding assistants produce code that works, passes review, and
solves the immediate task — but slowly fragments the architecture.

The patterns are subtle:
- Error handling that was once unified now has 4 implementations across modules
- Import boundaries that used to be clean now leak across layers
- Functions that look original but are near-duplicates of code elsewhere

These aren't bugs. Linters won't flag them. They compound silently until the
codebase resists change.

I built drift, a static analyzer focused specifically on this problem. It
measures six axes of architectural coherence: pattern fragmentation, layer
violations, near-duplicates, explainability gaps, file volatility, and system
misalignment.

Key design decisions:
- No LLMs in the pipeline. Deterministic, reproducible, fast.
- Designed for CI integration, not as a one-shot audit tool.
- Outputs SARIF for GitHub Code Scanning integration.
- Focus on actionable findings, not vanity metrics.

Not a pitch — genuinely curious how other teams track this kind of drift, and
whether deterministic static analysis is the right abstraction.

https://github.com/sauremilk/drift
```

**Posting-Hinweis:** Erfahrungsbasierter Diskussions-Ton. Kein "I built X"-Spam.

---

## 6. Twitter / X Thread (5 Tweets)

**Thread:**

```
🧵 1/5
AI coding tools optimize for the prompt, not the project.

The result: code that works locally but fragments your architecture globally.

I built an open-source tool to measure this. Here's what it found on real repos. ↓
```

```
2/5
The problem has a name: architectural drift.

- Error handling done 4 different ways in one module
- DB imports leaking into the API layer
- Copy-paste functions that diverged into near-duplicates

These aren't bugs. Linters won't catch them. But they compound.
```

```
3/5
drift runs 15 deterministic scoring signals, including:

• Pattern Fragmentation
• Architecture Violations
• Mutant Duplicates
• Explainability Deficit
• Temporal Volatility
• System Misalignment
+ 9 more (consistency, contract, cohesion, coupling)

No LLMs. Pure AST analysis. Reproducible.
```

```
4/5
On FastAPI (664 files): drift score 0.62, 360 findings.
On Django (2890 files): drift score 0.60, 969 findings.
On Frappe (1179 files): drift score 0.54, 913 findings.

Not a quality judgment — a coherence signal.
```

```
5/5
pip install -q drift-analyzer
drift analyze --repo .

- Rich terminal dashboard
- JSON + SARIF output
- GitHub Action: uses: sauremilk/drift@v1
- MIT licensed

→ https://github.com/sauremilk/drift
```

---

## 7. dev.to / Hashnode Artikel

**Titel:**

```
How Copilot silently fragments your architecture — and how to detect it with drift
```

**Tags:** `python`, `architecture`, `static-analysis`, `ai`

**Artikel:**

````markdown
## The problem nobody talks about

AI coding assistants are fast. They pass tests. They get approved in review.
But they optimize for one thing: the immediate prompt context.

They don't know your architecture. They don't know you already have a
`handle_auth_error()` function. They don't know that `src/db/` shouldn't import
from `src/api/`.

The result is a slow, invisible rot. Not bugs — erosion. Your codebase still
works, but it resists change more every week.

## What architectural drift looks like

Here's what drift found when I ran it on FastAPI (664 files, 3,902 functions):

- **Drift Score: 0.62** (high severity)
- **360 findings** across all signal families
- Top signal: System Misalignment — novel dependency patterns in multiple modules

On Django (2,890 files):
- **Drift Score: 0.60** — 969 findings
- Top signals: Explainability Deficit in admin module (complex functions without docs)

On Frappe (1,179 files):
- **Drift Score: 0.54** — 913 findings
- 92 error handling variants in `frappe/utils/` alone

This isn't "bad code." It's code that grew without coherent design pressure.

## The 15 signals

Drift measures 15 families of architectural erosion (6 core + 9 added in v0.7–v0.8). The core six:

**1. Pattern Fragmentation (PFS)**
Same concern implemented N different ways in the same module. Classic example:
error handling done with `try/except`, `if/else`, early returns, and custom
exceptions — all in the same package.

**2. Architecture Violations (AVS)**
Imports crossing layer boundaries. Database models imported in API routes.
Presentation logic reaching into domain internals.

**3. Mutant Duplicates (MDS)**
Functions that are 80–95% identical — the signature of copy-paste-then-modify.
Individually fine, collectively a maintenance burden.

**4. Explainability Deficit (EDS)**
Complex functions (high cyclomatic complexity, deep nesting) with no
docstrings, no type annotations, and no tests. Not wrong — but unexplainable.

**5. Temporal Volatility (TVS)**
Files changed by too many authors in too short a time. Hotspots where
ownership is unclear and merge conflicts are likely.

**6. System Misalignment (SMS)**
Recently introduced patterns that are foreign to their target module.
The function works, but its style doesn't match anything around it.

**Plus 9 additional signals** covering documentation gaps (DIA), boundary enforcement (BEM), third-party sprawl (TPD), god-class detection (GCD), naming drift (NBV), bloated API surfaces (BAT), exception contract violations (ECM), internal cohesion deficit (COD), and co-change coupling (CCC). See the [signal reference](https://sauremilk.github.io/drift/reference/signals/) for details.

## No LLMs. Deterministic. Fast.

Drift uses Python's built-in `ast` module, git history analysis, and
statistical comparison. No model calls, no API keys, no flaky results.

The same input always produces the same output. That's the foundation
for trust: reproducibility.

## Try it

```bash
pip install -q drift-analyzer
drift analyze --repo .
```

Or in CI:

```yaml
- uses: sauremilk/drift@v1
  with:
    fail-on: none
    upload-sarif: "true"
```

## What drift is not

- Not a linter (doesn't check style or formatting)
- Not a security scanner (doesn't find vulnerabilities)
- Not a test coverage tool

It's a structural coherence analyzer. Think of it as a code review assistant
that reads the whole codebase instead of just the diff.

## Links

- GitHub: [sauremilk/drift](https://github.com/sauremilk/drift)
- PyPI: [drift-analyzer](https://pypi.org/project/drift-analyzer/)
- Docs: [sauremilk.github.io/drift](https://sauremilk.github.io/drift/)
````

---

## 8. Discord-Server

**Empfohlene Server:**
- Python Discord (`#showcase` Channel)
- The Programmer's Hangout
- AI Engineer Discord

**Beispielpost:**

```
Built an open-source static analyzer for architectural drift — the kind of
structural erosion that happens when AI coding tools fragment your patterns,
cross layer boundaries, and accumulate near-duplicates.

15 deterministic scoring signals, no LLMs, fast. Pure AST + git history analysis.

pip install -q drift-analyzer && drift analyze --repo .

Feedback welcome: https://github.com/sauremilk/drift
```

---

## 9. PyPI Publishing (einmalig)

```bash
# 1. Trusted Publisher auf PyPI konfigurieren:
#    https://pypi.org/manage/account/publishing/
#    GitHub repo: sauremilk/drift
#    Workflow: publish.yml
#    Environment: pypi

# 2. Dann einfach einen neuen GitHub Release erstellen:
gh release create v1.1.0 --title "v1.1.0" --generate-notes
# → GitHub Action publish.yml baut und pushed automatisch zu PyPI
```

---

## 6. pre-commit.ci (automatische Indexierung)

Nach dem Pushen von `.pre-commit-hooks.yaml` wird drift automatisch auf
https://pre-commit.ci indexiert. Kein weiterer Schritt nötig.

Das Icon erscheint dann auf der pre-commit.ci-Seite und in deren Suchfunktion.
