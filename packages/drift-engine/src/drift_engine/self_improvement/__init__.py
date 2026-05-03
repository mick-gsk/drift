"""Self-Improvement Loop (DSOL) — ADR-097.

Deterministic, bounded, human-in-the-loop continuous-optimization
engine. Runs a single **cycle** per invocation: observes the current
drift state (repo self-scan + KPI trend), diagnoses regressive signals
and unreviewed hotspots, and emits **proposals only** — never a code
change, never an auto-merge.

Exposure points:
- ``drift self-improve run``: CLI for local or cron use.
- ``.github/workflows/self-improvement-loop.yml``: weekly cron that
  uploads the cycle artifact; a maintainer manually opens follow-up
  PRs.
- Ledger ``.drift/self_improvement_ledger.jsonl`` lets each cycle see
  what the previous cycle proposed so repeated signals earn higher
  priority scores (compounding optimization pressure).
"""

from __future__ import annotations

from .engine import (
    ClosedProposalEntry,
    ConvergenceStatus,
    CycleLedgerEntry,
    ImprovementProposal,
    ImprovementReport,
    SelfImprovementEngine,
    close_proposal,
    run_cycle,
)

__all__ = [
    "ClosedProposalEntry",
    "CycleLedgerEntry",
    "ConvergenceStatus",
    "ImprovementProposal",
    "ImprovementReport",
    "SelfImprovementEngine",
    "close_proposal",
    "run_cycle",
]
