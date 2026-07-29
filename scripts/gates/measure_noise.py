"""How often would the guard speak on code that is already in the repository?

Every file in a checked-out repository is existing, reviewed, working code. A
report on one of those files is not automatically wrong — real duplication
exists, and this measurement finds some — but a high rate means the guard is
noise in practice, whatever it scores on a fixture.

This exists because the fixture said 100 % recall and 0 false positives while
the guard, measured against five real repositories, would have spoken on
27–69 % of their files. Nothing in the test suite could have caught that: the
fixture is six files written to demonstrate the two signals.

Usage:

    git clone --depth 1 https://github.com/pallets/flask /tmp/corpus/flask
    python scripts/gates/measure_noise.py /tmp/corpus

Point it at a directory of checkouts. It builds an index per repository and
replays every file through the same lookups the PostToolUse hook runs.
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from drift.guard import build, extract, lookup, schema  # noqa: E402

#: Above this, the guard is interrupting rather than reporting. Chosen from the
#: measured spread (0.0-5.6 % across five repositories), not from taste.
NOISE_BUDGET_PERCENT = 10.0


def measure(repo: pathlib.Path) -> dict:
    started = time.perf_counter()
    stats = build.build_full(repo)
    build_seconds = time.perf_counter() - started

    conn = schema.connect(repo)
    if conn is None:
        return {"repo": repo.name, "files": 0, "rate": 0.0, "examples": []}

    files = [row[0] for row in conn.execute("SELECT path FROM files ORDER BY path")]
    spoke = 0
    duplicates = 0
    boundaries = 0
    examples: list[str] = []

    for rel in files:
        try:
            source = (repo / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        symbols, imports = extract.extract(source, pathlib.PurePosixPath(rel).suffix)
        hits = lookup.find_duplicates(conn, rel, symbols)
        duplicate_count = len(hits)
        hits += lookup.find_novel_edges(conn, rel, imports)
        if not hits:
            continue
        spoke += 1
        duplicates += duplicate_count
        boundaries += len(hits) - duplicate_count
        if len(examples) < 3:
            examples.append(f"{rel}: {hits[0].message}")

    conn.close()
    return {
        "repo": repo.name,
        "files": len(files),
        "symbols": stats["symbols"],
        "build_seconds": round(build_seconds, 2),
        "spoke_on": spoke,
        "rate": round(100.0 * spoke / max(1, len(files)), 1),
        "duplicates": duplicates,
        "boundaries": boundaries,
        "examples": examples,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    corpus = pathlib.Path(sys.argv[1])
    over_budget: list[str] = []

    for repo in sorted(p for p in corpus.iterdir() if p.is_dir()):
        result = measure(repo)
        print(
            f"\n{result['repo']:14} {result['files']:>5} files  "
            f"{result['symbols']:>6} symbols  build {result['build_seconds']:>5.2f}s"
        )
        print(
            f"{'':14} speaks on {result['spoke_on']:>4}/{result['files']} files "
            f"= {result['rate']}%  ({result['duplicates']} duplicate, "
            f"{result['boundaries']} boundary)"
        )
        for example in result["examples"]:
            print(f"{'':16}· {example}")
        if result["rate"] > NOISE_BUDGET_PERCENT:
            over_budget.append(f"{result['repo']} at {result['rate']}%")

    if over_budget:
        print(f"\nover the {NOISE_BUDGET_PERCENT}% noise budget: {', '.join(over_budget)}")
        return 1
    print(f"\nevery repository within the {NOISE_BUDGET_PERCENT}% noise budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
