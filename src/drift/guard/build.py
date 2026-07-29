"""Build the guard index from a repository.

Full builds walk every indexable source file once. Incremental updates touch
exactly one file, which is what the PostToolUse hook does after each edit.
"""

from __future__ import annotations

import hashlib
import pathlib
import time

from drift.guard import extract, schema

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".drift",
    ".drift-cache",
    "build",
    "dist",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}


def dir_of(rel_path: str) -> str:
    """Directory part of a repo-relative path; '.' for files at the root."""
    parent = str(pathlib.PurePosixPath(rel_path).parent)
    return parent if parent != "" else "."


def module_to_dir(module: str, known_dirs: set[str]) -> str | None:
    """Map a dotted module path onto a repository directory, if it is one."""
    parts = module.split(".")
    while parts:
        candidate = "/".join(parts)
        if candidate in known_dirs:
            return candidate
        parts.pop()
    return None


def relative_to_dir(specifier: str, src_dir: str, known_dirs: set[str]) -> str | None:
    """Resolve a `./x` or `../y/z` import onto a repository directory.

    A specifier can name either a directory (`../db`) or a module inside one
    (`../db/client`), and the guard cannot tell which without touching the
    disk. So it tries the resolved path as a directory first and falls back to
    its parent — exactly right for the file case, harmless otherwise.
    """
    base = "" if src_dir == "." else src_dir
    parts: list[str] = []
    for part in f"{base}/{specifier}".split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)

    candidate = "/".join(parts) if parts else "."
    if candidate in known_dirs:
        return candidate
    parent = dir_of(candidate)
    return parent if parent in known_dirs else None


def import_to_dir(specifier: str, src_dir: str, known_dirs: set[str]) -> str | None:
    """Map any import specifier onto a repository directory, if it is one.

    Bare TypeScript specifiers (`react`, `@scope/pkg`) name packages rather
    than places in this repository, so they resolve to nothing.
    """
    if specifier.startswith("."):
        return relative_to_dir(specifier, src_dir, known_dirs)
    if "/" in specifier:
        return None
    return module_to_dir(specifier, known_dirs)


def _iter_source_files(repo_root: pathlib.Path):
    for path in sorted(repo_root.rglob("*")):
        if path.suffix not in extract.GUARDED_SUFFIXES:
            continue
        rel = path.relative_to(repo_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if not path.is_file():
            continue
        yield rel.as_posix(), path


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_full(repo_root: pathlib.Path) -> dict:
    """Rebuild the index from scratch. Returns counts and elapsed time."""
    started = time.perf_counter()
    repo_root = pathlib.Path(repo_root)

    index_file = schema.index_path(repo_root)
    if index_file.exists():
        index_file.unlink()

    conn = schema.create(repo_root)
    schema.initialize(conn)

    collected = list(_iter_source_files(repo_root))
    known_dirs = {dir_of(rel) for rel, _ in collected}

    edge_counts: dict[tuple[str, str], int] = {}
    symbol_rows: list[tuple] = []
    file_rows: list[tuple] = []
    now = time.time()

    for rel, path in collected:
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        symbols, imports = extract.extract(source, path.suffix)
        src_dir = dir_of(rel)

        file_rows.append((rel, _sha256(path), now))
        symbol_rows.extend((rel, s.name, s.norm_name, s.kind, s.sig_hash, s.line) for s in symbols)
        for module in imports:
            dst_dir = import_to_dir(module, src_dir, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            edge_counts[(src_dir, dst_dir)] = edge_counts.get((src_dir, dst_dir), 0) + 1

    conn.executemany("INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)", file_rows)
    conn.executemany(
        "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        symbol_rows,
    )
    conn.executemany(
        "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, ?)",
        [(src, dst, count) for (src, dst), count in edge_counts.items()],
    )
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('built_at', ?)", (str(now),))
    conn.commit()
    conn.close()

    return {
        "files": len(file_rows),
        "symbols": len(symbol_rows),
        "edges": len(edge_counts),
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }


def update_file(repo_root: pathlib.Path, rel_path: str) -> None:
    """Refresh index rows for exactly one file. Silently no-ops without an index."""
    repo_root = pathlib.Path(repo_root)
    conn = schema.connect(repo_root)
    if conn is None or not schema.is_usable(conn):
        return

    path = repo_root / rel_path
    conn.execute("DELETE FROM symbols WHERE path = ?", (rel_path,))
    conn.execute("DELETE FROM files WHERE path = ?", (rel_path,))

    if path.exists():
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            conn.commit()
            conn.close()
            return
        symbols, imports = extract.extract(source, path.suffix)
        conn.executemany(
            "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [(rel_path, s.name, s.norm_name, s.kind, s.sig_hash, s.line) for s in symbols],
        )
        conn.execute(
            "INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)",
            (rel_path, _sha256(path), time.time()),
        )
        known_dirs = {row[0] for row in conn.execute("SELECT DISTINCT src_dir FROM import_edges")}
        known_dirs |= {dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
        src_dir = dir_of(rel_path)
        for module in imports:
            dst_dir = import_to_dir(module, src_dir, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            conn.execute(
                "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, 1)"
                " ON CONFLICT(src_dir, dst_dir) DO UPDATE SET count = count + 1",
                (src_dir, dst_dir),
            )

    conn.commit()
    conn.close()
