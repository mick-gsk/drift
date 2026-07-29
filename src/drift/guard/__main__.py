"""Lean command line for the guard hot path.

Deliberately argparse and not click: click alone costs tens of milliseconds
of import time on every hook invocation, and this entry point runs twice per
file edit.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from drift.guard import build, extract, lookup, report, schema


def _open_index(repo_root: pathlib.Path):
    conn = schema.connect(repo_root)
    if conn is None or not schema.is_usable(conn):
        return None
    return conn


def _cmd_build(args) -> int:
    stats = build.build_full(pathlib.Path(args.repo))
    print(json.dumps(stats))
    return 0


def _cmd_pre(args) -> int:
    """Brief the agent only when it is about to create a NEW file.

    Editing an existing file is the common case; speaking up every time would
    make the guard noise instead of signal. A new file is where duplication is
    actually born, and it is rare enough to be worth a sentence.
    """
    repo_root = pathlib.Path(args.repo)
    if (repo_root / args.file).exists():
        return 0

    conn = _open_index(repo_root)
    if conn is None:
        return 0
    targets = lookup.known_targets(conn, args.file)
    neighbours = lookup.neighbourhood(conn, args.file)
    conn.close()

    lines: list[str] = []
    if neighbours:
        lines.append(
            f"  - already defined in {build.dir_of(args.file)}/: {', '.join(neighbours)}"
        )
    if targets:
        lines.append(
            f"  - {build.dir_of(args.file)}/ so far imports only from: {', '.join(targets)}"
        )
    if not lines:
        return 0
    text = "\n".join(["drift:", *lines])[: report.MAX_MESSAGE_CHARS]
    print(text)
    return 0


def _cmd_reset(args) -> int:
    report.reset_counter(pathlib.Path(args.repo))
    return 0


def _cmd_post(args) -> int:
    repo_root = pathlib.Path(args.repo)
    conn = _open_index(repo_root)
    if conn is None:
        return 0

    path = repo_root / args.file
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        conn.close()
        return 0

    symbols, imports = extract.extract(source)
    hits = lookup.find_duplicates(conn, args.file, symbols)
    hits += lookup.find_novel_edges(conn, args.file, imports)
    conn.close()

    for hit in hits:
        report.bump(repo_root, hit.kind)

    build.update_file(repo_root, args.file)

    text = report.format_hits(hits)
    if text:
        print(text)
    return 0


def _cmd_stats(args) -> int:
    print(report.summary_line(report.read_counter(pathlib.Path(args.repo))))
    return 0


def _cmd_doctor(args) -> int:
    repo_root = pathlib.Path(args.repo)
    checks: list[tuple[bool, str]] = []

    index_file = schema.index_path(repo_root)
    checks.append((index_file.exists(), f"index present at {index_file}"))

    conn = schema.connect(repo_root)
    usable = conn is not None and schema.is_usable(conn)
    checks.append((usable, f"index schema version is {schema.SCHEMA_VERSION}"))

    file_count = 0
    if usable:
        file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        conn.close()
    checks.append((file_count > 0, f"index holds {file_count} file(s)"))

    for ok, label in checks:
        print(f"[{'x' if ok else ' '}] {label}")
    return 0 if all(ok for ok, _ in checks) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drift-guard", description="Drift agent guard.")
    parser.add_argument("--repo", dest="repo_global", default=".", help="Repository root.")
    sub = parser.add_subparsers(dest="command", required=True)

    # --repo is accepted on both sides of the subcommand: the hooks pass it
    # before (`drift-guard --repo X post ...`), humans naturally write it after
    # (`drift-guard build --repo X`). argparse binds an option to exactly one
    # parser, so it is declared twice and resolved below.
    def _add(name: str, help_text: str):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--repo", dest="repo_local", default=None, help="Repository root.")
        return p

    _add("build", "Build the guard index.")
    for name in ("pre", "post"):
        p = _add(name, f"Guard {name}-edit check.")
        p.add_argument("--file", required=True, help="Repo-relative file path.")
    _add("stats", "Print the session tally.")
    _add("reset", "Reset the session tally.")
    _add("doctor", "Check the guard installation.")

    args = parser.parse_args(argv)
    args.repo = args.repo_local or args.repo_global
    handlers = {
        "build": _cmd_build,
        "pre": _cmd_pre,
        "post": _cmd_post,
        "stats": _cmd_stats,
        "reset": _cmd_reset,
        "doctor": _cmd_doctor,
    }
    try:
        return handlers[args.command](args)
    except Exception as exc:  # never break the agent loop
        print(f"drift-guard: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
