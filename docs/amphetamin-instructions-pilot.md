# Amphetamin's throughput instructions: what a pilot measurement found

**Date:** 2026-07-30 · **Harness:** `scripts/gates/measure_amphetamin.py`
**Raw data:** 10 sessions, 5 per arm across two tasks · Claude Code headless, `stream-json` transcripts

Amphetamin ships two unlike things. The held stop is a mechanism with tests on
both branches. The four throughput instructions are advice injected at session
start, and README.md has said from the beginning that no speedup was measured.
This is the measurement.

## Method

Same task, same corpus, run with and without the four instructions appended to
the system prompt. Read-only work in a throwaway copy of this repository, so
runs cannot diverge after the first edit. The instruction text is read out of
`drift/guard/__main__.py` rather than restated, because measuring a copy would
prove nothing about the mode.

Counted from each transcript: assistant turns, tool calls, files read more than
once, ranged reads, output tokens, cost. Tool calls sit beside turns so a drop
in turns cannot be mistaken for the model doing less work.

## Results

### Task `map-modules` — "what is each module under src/drift/guard/ for?"

| metric | without | with |
|---|---|---|
| turns | 12, 12 | 12, 12 |
| tool calls | 9, 9 | 9, 9 |
| repeat reads | 0, 0 | 0, 0 |
| **ranged reads** | **4, 4** | **0, 0** |
| output tokens | 1600, 1481 | 1328, 1524 |
| cost (USD) | 0.478, 0.465 | 0.600, 0.604 |

### Task `find-symbol` — "where is anything named *duplicate* defined?"

| metric | without | with |
|---|---|---|
| turns | 8, 7, 6 | 8, 8, 6 |
| tool calls | 4, 4, 3 | 4, 5, 3 |
| repeat reads | 0, 0, 0 | 0, 0, 0 |
| ranged reads | 0, 0, 0 | 0, 0, 0 |
| output tokens | 1166, 1696, 1062 | 1422, 1413, 1067 |
| cost (USD) | 0.271, 0.303, 0.270 | 0.286, 0.286, 0.275 |

## What this shows

**No effect on turns or tool calls.** Identical in the first task, fully
overlapping ranges in the second. If the batching instruction changes anything,
the change is smaller than the run-to-run spread at this sample size.

**One instruction targets a behaviour that never happened.** "Do not re-read a
file you already read this session" — repeat reads were **0 in all ten
sessions, both arms**. There was nothing to prevent. That instruction cannot
improve anything here because the baseline was already perfect.

**One instruction moved the wrong way.** "Read the part you need" — the arm
*with* the instruction did **fewer** ranged reads, 4 → 0. Two runs per arm is
too little to call it harm, but it is not support either.

**The instructions cost money.** Higher in both tasks: +26 % on `map-modules`,
+3 % on `find-symbol`. They are ~640 characters on every request, and the
transcript shows that being paid for.

## What this does not show

It does not show the instructions have no effect. Five sessions per arm against
a stochastic model cannot establish that, and this document should not be cited
as if it could.

It does not judge answer quality. Grading was left out deliberately: without a
rubric, a mode that traded correctness for turns would score as an improvement.

Every session was rate-limited, so wall-clock time is not reported.

## What proving an effect would cost

`find-symbol` turns ranged 6–8 across three runs. Detecting a 10 % change —
roughly 0.7 turns — against that spread needs on the order of 30 sessions per
arm. At the observed \$0.27–0.60 per session that is **\$40–70 per task**, plus
hours of rate-limited waiting, for one metric on one corpus.

## Recommendation

Delete the four instructions and keep the mechanism.

The cheap measurement found no benefit and a measurable cost. The expensive
measurement that could still find a small benefit costs more than the benefit
could plausibly be worth, and one of the four instructions is already known to
address a non-problem. Amphetamin then describes exactly what it does: it holds
one stop per session when the index recorded work left behind. That claim has
tests. This one does not.

Reproduce with:

```bash
python scripts/gates/measure_amphetamin.py --runs 3 --out results.json
```
