---
description: Check that the drift guard is installed, indexed and answering.
---

Run `drift-guard doctor` in the repository root and show its output as a checklist.

If any line shows `[ ]`, run `drift-guard build`, show the result, then run
`drift-guard doctor` again. Report what the commands printed — do not judge the
installation healthy on any other basis.
