---
description: Turn amphetamin on or off — keep sessions running on machine-checked open work.
---

Run `drift-guard amph $ARGUMENTS` in the repository root and show the output.

With no argument it reports the current state. `on` and `off` switch the mode
and reset this session's counters.

If the user asks what the mode does, tell them exactly this and nothing more:

- **What it does:** while on, the `Stop` hook refuses **one** stop per session
  when drift's index recorded a symbol introduced during that session which
  already existed elsewhere. It hands back a specific, finishable instruction
  and never asks twice. It also injects a short set of throughput instructions
  at session start: batch independent tool calls, do not re-read unchanged
  files, prefer ranged reads, keep going while the next step is determined.
- **What it does not do:** it does not skip permission prompts, truncate reads,
  shorten plans, skip verification or lower any threshold. The prompt on `Read`
  is the user's only view of what an agent reaches for, and repository content
  is a prompt-injection surface — removing it would buy convenience with a real
  control.
- **What is guaranteed and what is not:** the single held stop is a mechanism —
  it either fires or it does not, and there is a test for it. The throughput
  instructions are instructions; nothing enforces them, and no speedup has been
  measured. Say so if asked.
