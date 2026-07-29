# Claude Code Plugin

**Your agent is about to build it twice. Drift tells it first.**

```bash
/plugin marketplace add mick-gsk/drift
/plugin install drift@drift
```

Restart Claude Code, then run `/drift:doctor`. Those two lines are the whole
install: the guard imports nothing but the standard library and runs from the
plugin itself, so there is no `pip install`, no dependency to resolve and
nothing to configure. It writes **nothing into your repositories** — the index
lives in your cache (`~/.cache/drift`, or `$XDG_CACHE_HOME/drift`), keyed by
repository path, because a plugin that fires in every project you open has no
business leaving a directory in each of them. A project that wants the index
alongside its source opts in by creating a `.drift/` directory; `DRIFT_CACHE_HOME`
overrides both.

!!! note "Python, TypeScript, JavaScript, Go, Rust, Java, Kotlin and C#"
    `.py .ts .tsx .js .jsx .mjs .cjs .go .rs .java .kt .kts .cs`, all in one index — a name defined in
    Python is found from Go, because `validate_token`, `validateToken` and
    `ValidateToken` all normalise to the same thing. Python is parsed with `ast`;
    the others are matched against top-level declarations,
    because the guard may not grow a parser dependency. That trade costs recall,
    never precision: every pattern is anchored to column zero and to a
    declaration keyword, so a miss is possible and an invented symbol is not.
    Edits to other languages pass through untouched.

## What it says

After every edit your agent makes, drift says one of two things — or, most of
the time, nothing at all:

```text
drift:
  - `validate_token` already exists in src/auth/tokens.py:44
  - first import from src/api/ into src/db/ anywhere in this repository
```

Two questions, asked of a SQLite index of your repository:

1. **Does this symbol already exist somewhere else?** Names are normalised and
   signatures hashed, so `validateToken` and `validate_token(token, audience)`
   still match.
2. **Has this directory ever imported from that one?** Boundaries are
   *observed*, not configured. The index records which directory-to-directory
   imports your repository actually contains, so a first-ever crossing stands
   out without you writing a rule.

Silence is the normal case, not a failure. `/drift:stats` shows what the guard
caught during the current session.

## What that looks like in a real session

Asked to write a function that already existed elsewhere, with the guard
installed and no other instruction, Claude came back with this on its own:

> Created `src/api/schemas.py:1` with just that function.
>
> One thing worth flagging: the drift guard reports a `validate_token` already
> exists at `src/auth/tokens.py:4`. I didn't look at it, per your instruction —
> so I don't know whether it's a real implementation this one now shadows.
> Worth a check before anything imports the new one.

Nobody asked it to check for duplicates. The guard put the fact in front of it,
and it did the rest. One run, unedited. The same session's debug log shows all
four hooks firing: `SessionStart` 282 characters of routing, `PreToolUse` 100,
`PostToolUse` 86.

## Why it can run inside the agent loop

The guard is a separate module that imports only `sqlite3`, `ast` and `json` —
no `click`, no `rich`, no ML stack, nothing from the analysis engine. That
constraint is enforced by a test, not by intention.

| Measured on the drift repository (344 Python files) | p50 | p95 |
|---|---|---|
| Before an edit to a new file | 70 ms | 72 ms |
| After an edit to an existing file | 86 ms | 87 ms |
| *Python interpreter startup alone, for reference* | *24 ms* | *29 ms* |
| *`import drift.cli`, the path the guard avoids* | *3229 ms* | *3959 ms*  |

20 runs each, cold, macOS/arm64, Python 3.12 — recorded in
[`benchmark_results/guard_baseline.json`](https://github.com/mick-gsk/drift/blob/main/benchmark_results/guard_baseline.json).

If the guard breaks, it stays silent and the session continues. It can report,
but it can never block.

## How it works

| Piece | What it does |
|---|---|
| `index.db` | SQLite: module-level symbols, their normalised names and signature hashes, and every directory-to-directory import edge the repository contains |
| `drift-guard` | Lean entry point. Reads the index, parses at most the one file that changed |
| Four hooks | `SessionStart` builds or refreshes the index in the background · `PreToolUse` briefs the agent before it creates a new file · `PostToolUse` reports what the edit introduced · `Stop` shows the session tally |

The index is built once and updated per changed file. It is a cache and nothing
more: delete the directory `/drift:doctor` prints and the next session rebuilds
it. Nothing is written into the repository being analysed.

## Commands

| Command | Purpose |
|---|---|
| `/drift:doctor` | Check that the guard is installed, indexed and answering |
| `/drift:stats` | Show what the guard caught this session |

Both are thin wrappers around `drift-guard doctor` and `drift-guard stats`,
which you can also run directly.

## Troubleshooting

**`/drift:doctor` shows `[ ]` for the index.** Run `drift-guard build` in the
repository root. A full build of a 344-file repository takes about 6 seconds.

**The guard never says anything.** That is the expected case for most edits.
To confirm it is alive, create a Python file containing a function whose name
already exists elsewhere in the repository — the report should appear right
after the write.

**Nothing loaded at all.** Confirm the hook scripts are executable
(`chmod +x hooks/guard-*.sh`); Claude Code skips a hook whose script lacks the
execute bit.
