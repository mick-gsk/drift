---
title: "Prove It Yourself"
description: "Run drift on your own repo. See findings you can verify. No config, no sign-up, no cloud."
---

# Your Repo. Your Results.

A benchmark on someone else's code proves nothing to you.
Run drift on a repo you know — and judge the findings yourself.

---

## 1. One command

=== "Zero-install (uvx)"

    ```bash
    uvx drift-analyzer analyze --repo . --format json --compact > drift-results.json
    ```

=== "pip"

    ```bash
    pip install drift-analyzer
    drift analyze --repo . --format json --compact > drift-results.json
    ```

=== "pipx"

    ```bash
    pipx run drift-analyzer analyze --repo . --format json --compact > drift-results.json
    ```

=== "Docker"

    ```bash
    docker run --rm -v "$(pwd):/repo" ghcr.io/mick-gsk/drift:latest analyze --repo /repo --format json --compact > drift-results.json
    ```

**What happens:** Drift scans AST structure and git history of your local repo. Nothing is uploaded. No cloud, no account, no config file needed.

---

## 2. Drop your results

Drag the `drift-results.json` file into the box below — or paste the JSON content from your clipboard.

<div class="drift-prove-drop" data-max-findings="5" data-results-target="drift-prove-full-results" style="margin-top: 1rem;">
  <span class="drift-prove-drop-icon">&#128462;</span>
  Drop <strong>drift-results.json</strong> here<br>
  <button data-prove-paste>paste from clipboard</button> · <label>browse<input type="file" accept=".json" data-prove-file></label>
</div>
<div id="drift-prove-full-results" class="drift-prove-results" hidden></div>
<p class="drift-prove-privacy">&#128274; Your data never leaves your browser. This viewer runs entirely client-side. No server, no analytics, no cookies.</p>

---

## 3. Check the findings yourself

Don't take drift's word for it. Here are three things to verify against your own knowledge:

### The finding you already knew about

Every codebase has that one module that grew too fast, that one file everyone avoids, that one pattern that got copy-pasted three times. Look at the top findings — **do you recognize the files?**

If drift flagged something you've been meaning to fix anyway, that's not a coincidence. That's signal.

### The duplicate you didn't notice

Look for **MDS** (Mutant Duplicates) findings. These are functions that look almost identical but live in different files — the classic artifact of AI-assisted development where each prompt produces a self-contained solution.

Ask yourself: are those functions really different? Do they need to exist separately?

### The import that shouldn't be there

Look for **AVS** (Architecture Violation) findings. These flag imports that cross layer boundaries — a database import in your API layer, a utility reaching into core business logic.

Check: is the import direction intentional, or did it creep in during a fast iteration?

---

## 4. What if drift found nothing?

That's fine. It happens when:

- The repo has fewer than ~10 Python files
- Git history is shallow (less than 50 commits)
- The codebase is genuinely well-structured

None of these invalidate the tool. Small repos simply have less surface for structural drift to develop. Try it on a larger project.

## 5. What if drift found something real?

That's the proof. Not our proof — yours.

**Next steps:**

- [Finding Triage](getting-started/finding-triage.md) — how to read and prioritize findings
- [Prompts to Try](getting-started/prompts.md) — ask your AI agent to explain and fix findings
- [CI Integration](integrations.md) — add drift to your pipeline so findings don't regress

## 6. What if a finding is wrong?

False positives exist. Drift is at 97.3% precision — which means roughly 1 in 37 findings may be inaccurate.

If you spot one:

- [Troubleshooting](getting-started/troubleshooting.md) — common causes and workarounds
- [Open an issue](https://github.com/mick-gsk/drift/issues/new) — we treat every false positive report as a bug

---

<p style="text-align: center; font-size: 0.92rem; color: var(--md-default-fg-color--light); margin-top: 2rem;">
  <em>A proof you construct can be disputed. A proof you initiate cannot be denied.</em>
</p>
