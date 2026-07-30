"""Does amphetamin's throughput advice actually change how a session runs?

The mode ships two very different things. The held stop is a mechanism: it
fires or it does not, and `tests/guard/test_amphetamin.py` covers both. The
four throughput instructions are advice — nothing enforces them, and until now
nothing measured them either. README.md said so plainly, which is honest and
also an open question sitting in a shipped feature.

This answers it the only way that counts: run the same task with and without
the instructions, many times, and count what came out.

    python scripts/gates/measure_amphetamin.py --runs 3 --out results.json

What it measures, per session, from the `stream-json` transcript:

* **turns** — assistant messages. The instruction "issue independent tool calls
  in one batch" predicts fewer.
* **tool_calls** — total tool uses. Batching does not reduce these; it packs
  them into fewer turns. Reported so a drop in turns cannot be mistaken for
  the model simply doing less.
* **repeat_reads** — files read more than once. Directly targeted by "do not
  re-read a file you already read".
* **ranged_reads** — Read calls carrying offset/limit, targeted by "read the
  part you need".
* **output_tokens**, **duration_s** — what the user actually pays.

Two things this deliberately does not do. It does not judge whether the answer
was good; that would need a rubric and a grader, and a mode that trades
correctness for turns would look like an improvement here. And it does not
report a single number: with a handful of runs against a stochastic model the
spread is the finding, so every metric comes back with its full sample.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

#: Kept in sync with the constant the guard injects, by reading it rather than
#: restating it — a measurement of a copy would prove nothing about the mode.
GUARD_MAIN = pathlib.Path(__file__).resolve().parents[2] / "src" / "drift" / "guard" / "__main__.py"

#: Read-only work. Anything that edits would make runs diverge after the first
#: tool call, and then the arms are no longer comparable.
TASKS = {
    "map-modules": (
        "In one sentence each, say what every module directly inside "
        "src/drift/guard/ is responsible for. No preamble."
    ),
    "find-symbol": (
        "List every place a function or class whose name mentions 'duplicate' "
        "is defined under src/. Give file and line, nothing else."
    ),
}


def instruction_text() -> str:
    """The four instructions, lifted from the guard rather than retyped."""
    source = GUARD_MAIN.read_text(encoding="utf-8")
    match = re.search(r"AMPHETAMIN_TEXT = \((.*?)\n\)", source, re.DOTALL)
    if match is None:  # pragma: no cover - the constant is covered by its own tests
        raise SystemExit("AMPHETAMIN_TEXT not found in the guard; the harness is stale.")
    return (
        "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1)))
        .encode()
        .decode("unicode_escape")
    )


def _metrics(events: list[dict]) -> dict | None:
    """Metrics for one session, or None when the session did not really run.

    The first pilot recorded a rate-limited session as `turns=1, tool_calls=0,
    output_tokens=0` and put it in the table beside real numbers, where it read
    as a dramatic improvement. A harness that reports a failed run as a
    measurement is worse than no harness, so a session counts only if it
    finished successfully, and a session that waited on a rate limit has a
    meaningless wall clock and says so.
    """
    turns = tool_calls = ranged_reads = 0
    read_targets: list[str] = []
    result: dict | None = None
    rate_limited = False

    for event in events:
        if event.get("type") == "assistant":
            turns += 1
            for block in event.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                tool_calls += 1
                if block.get("name") == "Read":
                    args = block.get("input", {})
                    read_targets.append(str(args.get("file_path", "")))
                    if args.get("offset") is not None or args.get("limit") is not None:
                        ranged_reads += 1
        elif event.get("type") == "rate_limit_event":
            rate_limited = True
        elif event.get("type") == "result":
            result = event

    if result is None or result.get("is_error") or result.get("subtype") != "success":
        return None

    usage = result.get("usage") or {}
    return {
        "turns": turns,
        "tool_calls": tool_calls,
        "repeat_reads": len(read_targets) - len(set(read_targets)),
        "ranged_reads": ranged_reads,
        "output_tokens": int(usage.get("output_tokens", 0)),
        "cost_usd": float(result.get("total_cost_usd") or 0.0),
        "api_ms": int(result.get("duration_api_ms") or 0),
        "rate_limited": rate_limited,
    }


def run_once(task: str, repo: pathlib.Path, extra_prompt: str | None) -> dict | None:
    """One headless session in a throwaway copy of the corpus."""
    workdir = pathlib.Path(tempfile.mkdtemp())
    try:
        target = workdir / "repo"
        shutil.copytree(repo, target, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__"))
        argv = [
            "claude",
            "-p",
            task,
            "--output-format",
            "stream-json",
            "--verbose",
            # Read-only by tool policy rather than by plan mode: plan mode ends
            # in an approval step, which would land in the turn count as an
            # artefact of the harness instead of the behaviour being measured.
            "--permission-mode",
            "acceptEdits",
            "--disallowedTools",
            "Write,Edit,NotebookEdit,Bash",
        ]
        if extra_prompt:
            argv += ["--append-system-prompt", extra_prompt]

        started = time.monotonic()
        proc = subprocess.run(
            argv, cwd=target, capture_output=True, text=True, timeout=600, check=False
        )
        elapsed = time.monotonic() - started

        events = []
        for line in proc.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        if not events:
            print(f"    no transcript: {proc.stderr.strip()[:160]}", file=sys.stderr)
            return None

        result = _metrics(events)
        if result is None:
            print("    session did not complete; discarded", file=sys.stderr)
            return None
        # Wall clock is only comparable when nothing waited on a rate limit.
        result["duration_s"] = None if result["rate_limited"] else round(elapsed, 1)
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _summary(samples: list[dict], key: str) -> dict:
    values = [s[key] for s in samples if s.get(key) is not None]
    return {
        "median": statistics.median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "samples": values,
    }


METRICS = (
    "turns",
    "tool_calls",
    "repeat_reads",
    "ranged_reads",
    "output_tokens",
    "api_ms",
    "cost_usd",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Sessions per arm per task.")
    parser.add_argument("--repo", default=".", help="Corpus to run against.")
    parser.add_argument("--out", default=None, help="Write the raw result JSON here.")
    args = parser.parse_args()

    repo = pathlib.Path(args.repo).resolve()
    instructions = instruction_text()
    arms = {"without": None, "with": instructions}
    results: dict = {"runs": args.runs, "repo": str(repo), "tasks": {}}

    for task_name, task in TASKS.items():
        print(f"\n=== {task_name} ===")
        results["tasks"][task_name] = {}
        for arm_name, extra in arms.items():
            samples = []
            for i in range(args.runs):
                print(f"  {arm_name} {i + 1}/{args.runs} ...", flush=True)
                sample = run_once(task, repo, extra)
                if sample is not None:
                    samples.append(sample)
            results["tasks"][task_name][arm_name] = {
                "n": len(samples),
                "rate_limited": sum(1 for s in samples if s["rate_limited"]),
                **{metric: _summary(samples, metric) for metric in METRICS},
            }

    print("\n" + "=" * 72)
    for task_name, arms_result in results["tasks"].items():
        print(f"\n{task_name}")
        print(f"  {'metric':<15}{'without':>22}{'with':>22}")
        for metric in METRICS:
            a, b = arms_result["without"], arms_result["with"]
            left = f"{a[metric]['median']} ({a[metric]['min']}–{a[metric]['max']})"
            right = f"{b[metric]['median']} ({b[metric]['min']}–{b[metric]['max']})"
            print(f"  {metric:<15}{left:>22}{right:>22}")
        a, b = arms_result["without"], arms_result["with"]
        print(
            f"  n = {a['n']} / {b['n']} sessions completed"
            f" (rate-limited: {a['rate_limited']} / {b['rate_limited']})"
        )

    print(
        "\nRanges are min–max over the samples. Where they overlap, this run"
        "\nfound no effect — it did not find that there is none."
    )

    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"\nRaw results: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
