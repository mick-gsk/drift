"""Measure wall-clock latency of a command over N cold process starts.

Gate G1 of the Drift Agent Guard plan: the in-loop guard must stay under
150 ms p95. This harness is the single source of truth for that number, so
that every claim about latency is reproducible instead of asserted.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time


def measure(command: list[str], runs: int, cwd: str | None = None) -> dict:
    """Run `command` `runs` times and return latency percentiles in ms."""
    durations: list[float] = []
    failures = 0
    for _ in range(runs):
        start = time.perf_counter()
        proc = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        durations.append((time.perf_counter() - start) * 1000.0)
        if proc.returncode != 0:
            failures += 1

    durations.sort()
    # Nearest-rank p95: smallest value at or above 95% of the sorted samples.
    p95_index = max(0, min(len(durations) - 1, int(round(0.95 * len(durations))) - 1))
    p50_index = max(0, min(len(durations) - 1, int(round(0.50 * len(durations))) - 1))
    return {
        "command": " ".join(command),
        "runs": runs,
        "p50_ms": round(durations[p50_index], 2),
        "p95_ms": round(durations[p95_index], 2),
        "min_ms": round(durations[0], 2),
        "max_ms": round(durations[-1], 2),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure command latency.")
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--out", default=None, help="Write JSON result here.")
    parser.add_argument("--label", default=None, help="Name for this measurement.")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        parser.error("no command given")

    result = measure(args.command, runs=args.runs)
    if args.label:
        result["label"] = args.label
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
