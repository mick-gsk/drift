"""Answer the two guard questions with index lookups only.

1. Does this symbol already exist somewhere else?
2. Does this import cross a directory boundary that has never been crossed?
"""

from __future__ import annotations

import sqlite3
from typing import NamedTuple

from drift.guard import build, extract


class Hit(NamedTuple):
    kind: str
    message: str


def find_duplicates(
    conn: sqlite3.Connection, rel_path: str, symbols: list[extract.Symbol]
) -> list[Hit]:
    """Symbols that already exist elsewhere in the repository."""
    hits: list[Hit] = []
    for symbol in symbols:
        if symbol.norm_name in extract.STOPWORDS:
            continue
        row = conn.execute(
            "SELECT path, name, line FROM symbols"
            " WHERE norm_name = ? AND path != ? ORDER BY path LIMIT 1",
            (symbol.norm_name, rel_path),
        ).fetchone()
        if row is None:
            continue
        other_path, other_name, other_line = row
        hits.append(
            Hit(
                kind="duplicate",
                message=(
                    f"`{symbol.name}` already exists as `{other_name}` in {other_path}:{other_line}"
                ),
            )
        )
    return hits


def find_novel_edges(conn: sqlite3.Connection, rel_path: str, imports: list[str]) -> list[Hit]:
    """Imports that introduce a directory-to-directory edge seen nowhere yet."""
    known_dirs = {build.dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
    src_dir = build.dir_of(rel_path)
    existing = {
        row[0]
        for row in conn.execute("SELECT dst_dir FROM import_edges WHERE src_dir = ?", (src_dir,))
    }

    hits: list[Hit] = []
    reported: set[str] = set()
    for module in imports:
        dst_dir = build.import_to_dir(module, src_dir, known_dirs)
        if dst_dir is None or dst_dir == src_dir:
            continue
        if dst_dir in existing or dst_dir in reported:
            continue
        reported.add(dst_dir)
        hits.append(
            Hit(
                kind="boundary",
                message=(
                    f"first import from {src_dir}/ into {dst_dir}/ anywhere in this repository"
                ),
            )
        )
    return hits


def neighbourhood(conn: sqlite3.Connection, rel_path: str, limit: int = 8) -> list[str]:
    """Symbol names that already live in the same directory."""
    src_dir = build.dir_of(rel_path)
    like = "%" if src_dir == "." else f"{src_dir}/%"
    rows = conn.execute(
        "SELECT DISTINCT name FROM symbols WHERE path LIKE ? AND path != ? ORDER BY name LIMIT ?",
        (like, rel_path, limit),
    )
    return [row[0] for row in rows]


def known_targets(conn: sqlite3.Connection, rel_path: str) -> list[str]:
    """Directories this file's directory already imports from."""
    src_dir = build.dir_of(rel_path)
    rows = conn.execute(
        "SELECT dst_dir FROM import_edges WHERE src_dir = ? ORDER BY dst_dir", (src_dir,)
    )
    return [row[0] for row in rows]
