"""Answer the two guard questions with index lookups only.

1. Does this symbol already exist somewhere else?
2. Does this import cross a directory boundary that has never been crossed?
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import NamedTuple

from drift.guard import build, extract


class Hit(NamedTuple):
    kind: str
    message: str


#: Path segments whose contents repeat names on purpose. Measured against five
#: real repositories: fastapi's `docs_src/` defines `Item` in over a hundred
#: tutorial files, date-fns ships the same example under `cjs/`, `cts/`, `esm/`,
#: and every test suite reuses helper and fixture names. Reporting those as
#: duplicates is not merely useless, it is the difference between a guard that
#: speaks on 2 % of edits and one that speaks on half of them.
_REPEATING_DIRS = frozenset(
    {
        "test",
        "tests",
        "__tests__",
        "spec",
        "specs",
        "testdata",
        "fixtures",
        "__fixtures__",
        "benchmarks",
        "migrations",
        "examples",
        "docs_src",
        "samples",
        "demos",
    }
)

#: Only when they are the first path segment. `com/example` is the package name
#: every Java scaffold generates, and reading it as a demonstration directory
#: switched the guard off for most of Java. The plural forms above are safe
#: anywhere; the singular ones are a word that appears inside real namespaces.
_REPEATING_ROOT_DIRS = frozenset({"example", "demo", "sample"})

#: A name shorter than this carries no evidence on its own. `add`, `date` and
#: `argv` all collide across unrelated files in real repositories.
MIN_DUPLICATE_NAME_LENGTH = 6

#: Above this many other definitions, a repeated name is a convention rather
#: than an accident, and saying so is worse than saying nothing. date-fns
#: implements the same `formatLong` and `localize` in 93 locale directories:
#: the author of the 94th knows. A name that exists once elsewhere is the
#: signal this guard was built for; a name that exists ninety times is the
#: shape of the codebase.
MAX_DUPLICATE_OCCURRENCES = 3

#: Kinds that can meaningfully duplicate each other. A function named `request`
#: and a class named `Request` are not the same thing, and reporting them as
#: duplicates was the single most convincing-looking false positive in the
#: measurement — plausible enough that a reader might believe it.
_KIND_GROUP = {
    "function": "callable",
    "binding": "callable",
    "class": "type",
    "type": "type",
}


def repeats_by_design(rel_path: str) -> bool:
    """True for paths whose whole purpose is to restate the same names.

    Directory *and* filename, because the two conventions coexist: pytest puts
    `test_x.py` under `tests/`, date-fns puts `test.ts` beside the source it
    covers, and both reuse helper names across files by design.
    """
    parts = rel_path.split("/")
    if any(part in _REPEATING_DIRS for part in parts):
        return True
    if parts and parts[0] in _REPEATING_ROOT_DIRS:
        return True
    # `Newtonsoft.Json.Tests` — .NET names a test project after the project it
    # covers, so the segment is never exactly "tests".
    if any(part.lower().endswith((".tests", ".test", ".specs", ".spec")) for part in parts[:-1]):
        return True

    stem = parts[-1].rsplit(".", 1)[0]
    if stem in ("test", "spec") or stem.startswith(("test_", "test-")):
        return True
    if stem.endswith(("_test", "-test", ".test", ".spec", "_spec")):
        return True
    # Generated code restates whatever it was generated from, and no one edits
    # it: `Model.designer.cs`, `Api.g.cs`, `Schema.generated.ts`.
    if stem.lower().endswith((".designer", ".g", ".generated", "_pb2", "_pb")):
        return True
    # Build scripts are configuration that happens to be written in a
    # programming language. `okhttp.jvm-conventions.gradle.kts` and its
    # siblings all declare `library`, and a Gradle file reaching into
    # build-logic is not an architectural event.
    name = parts[-1].lower()
    return name.endswith((".gradle.kts", ".gradle")) or name in ("build.sbt", "conftest.py")


def find_duplicates(
    conn: sqlite3.Connection, rel_path: str, symbols: list[extract.Symbol]
) -> list[Hit]:
    """Symbols that already exist elsewhere in the repository."""
    if repeats_by_design(rel_path):
        return []

    hits: list[Hit] = []
    for symbol in symbols:
        if symbol.norm_name in extract.STOPWORDS:
            continue
        if len(symbol.norm_name) < MIN_DUPLICATE_NAME_LENGTH:
            continue
        # `__getattr__` and friends are language protocol, not names anyone chose.
        if symbol.name.startswith("__") and symbol.name.endswith("__"):
            continue
        group = _KIND_GROUP.get(symbol.kind)
        if group is None:
            continue
        row = _first_real_match(conn, symbol, rel_path, group)
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


def _first_real_match(
    conn: sqlite3.Connection, symbol: extract.Symbol, rel_path: str, group: str
) -> tuple | None:
    """The first definition elsewhere that is the same sort of thing.

    Filtering happens in Python rather than SQL because the two conditions —
    kind group and path shape — do not fit a column each, and the candidate
    list for one normalised name is short by construction.
    """
    own_package = _package_of(conn, rel_path)
    rows = conn.execute(
        "SELECT s.path, s.name, s.line, s.kind, COALESCE(f.package_root, '.')"
        " FROM symbols s LEFT JOIN files f ON f.path = s.path"
        " WHERE s.norm_name = ? AND s.path != ? ORDER BY s.path",
        (symbol.norm_name, rel_path),
    )
    candidates = [
        (path, name, line)
        for path, name, line, kind, package in rows
        if _KIND_GROUP.get(kind) == group
        and not repeats_by_design(path)
        # Two packages in a workspace have their own namespaces. ripgrep's
        # `crates/cli` and `crates/globset` both define `escape`, and neither
        # author would call that duplication.
        and package == own_package
    ]
    if not candidates or len(candidates) > MAX_DUPLICATE_OCCURRENCES:
        return None
    return candidates[0]


def _package_of(conn: sqlite3.Connection, rel_path: str) -> str:
    """The package an edited file belongs to.

    The file may be brand new and absent from the index, so the answer falls
    back to any indexed file sharing its directory.
    """
    row = conn.execute("SELECT package_root FROM files WHERE path = ?", (rel_path,)).fetchone()
    if row is not None:
        return str(row[0])

    directory = build.dir_of(rel_path)
    like = "%" if directory == "." else f"{directory}/%"
    row = conn.execute(
        "SELECT package_root FROM files WHERE path LIKE ? LIMIT 1", (like,)
    ).fetchone()
    return str(row[0]) if row is not None else "."


def find_novel_edges(conn: sqlite3.Connection, rel_path: str, imports: list[str]) -> list[Hit]:
    """Imports that introduce a directory-to-directory edge seen nowhere yet."""
    # A tutorial reaching into the library it teaches is not an architectural
    # event. Measured on fastapi, `docs_src/` supplied most of what this signal
    # would have announced.
    if repeats_by_design(rel_path):
        return []

    known_dirs = {build.dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
    src_dir = build.dir_of(rel_path)
    existing = {
        row[0]
        for row in conn.execute("SELECT dst_dir FROM import_edges WHERE src_dir = ?", (src_dir,))
    }

    hits: list[Hit] = []
    reported: set[str] = set()
    for module in imports:
        dst_dir = build.import_to_dir(
            module, src_dir, known_dirs, pathlib.PurePosixPath(rel_path).suffix
        )
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
    """Everything already defined in this directory, or nothing at all.

    Two rules, both learned from measuring this on real repositories, where the
    briefing fired on 201 of fastapi's 203 directories and offered lists like
    `Termynal, handleSponsorImages, main, openLinksInNewTab, shuffle`.

    The names are filtered exactly as duplicate candidates are: a directory
    containing `main` and `setup` tells an agent nothing it can act on.

    And the list is returned only when it is *complete*. An alphabetical slice
    of a fifty-symbol directory, printed as "already defined in src/api/",
    reads as the contents of that directory and is not — the first eight names
    alphabetically are the ones least likely to be the relevant ones. A partial
    answer that looks whole is worse than silence.
    """
    if repeats_by_design(rel_path):
        return []

    src_dir = build.dir_of(rel_path)
    like = "%" if src_dir == "." else f"{src_dir}/%"
    rows = conn.execute(
        "SELECT DISTINCT name FROM symbols WHERE path LIKE ? AND path != ? ORDER BY name",
        (like, rel_path),
    )
    names = [
        name
        for (name,) in rows
        if extract.normalize(name) not in extract.STOPWORDS
        and len(extract.normalize(name)) >= MIN_DUPLICATE_NAME_LENGTH
        and not (name.startswith("__") and name.endswith("__"))
    ]
    return names if 0 < len(names) <= limit else []


def known_targets(conn: sqlite3.Connection, rel_path: str) -> list[str]:
    """Directories this file's directory already imports from."""
    if repeats_by_design(rel_path):
        return []

    src_dir = build.dir_of(rel_path)
    rows = conn.execute(
        "SELECT dst_dir FROM import_edges WHERE src_dir = ? ORDER BY dst_dir", (src_dir,)
    )
    return [row[0] for row in rows]
