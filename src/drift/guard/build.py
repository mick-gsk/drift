"""Build the guard index from a repository.

Full builds walk every Python file once. Incremental updates touch exactly
one file, which is what the PostToolUse hook does after each edit.
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


def _iter_python_files(repo_root: pathlib.Path):
    for path in sorted(repo_root.rglob("*.py")):
        rel = path.relative_to(repo_root)
        if any(part in SKIP_DIRS for part in rel.parts):
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

    conn = schema.connect(repo_root, create=True)
    schema.initialize(conn)

    collected = list(_iter_python_files(repo_root))
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
        symbols, imports = extract.extract(source)
        src_dir = dir_of(rel)

        file_rows.append((rel, _sha256(path), now))
        symbol_rows.extend(
            (rel, s.name, s.norm_name, s.kind, s.sig_hash, s.line) for s in symbols
        )
        for module in imports:
            dst_dir = module_to_dir(module, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            edge_counts[(src_dir, dst_dir)] = edge_counts.get((src_dir, dst_dir), 0) + 1

    conn.executemany(
        "INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)", file_rows
    )
    conn.executemany(
        "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        symbol_rows,
    )
    conn.executemany(
        "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, ?)",
        [(src, dst, count) for (src, dst), count in edge_counts.items()],
    )
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('built_at', ?)", (str(now),)
    )
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
        symbols, imports = extract.extract(source)
        conn.executemany(
            "INSERT INTO symbols (path, name, norm_name, kind, sig_hash, line)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (rel_path, s.name, s.norm_name, s.kind, s.sig_hash, s.line)
                for s in symbols
            ],
        )
        conn.execute(
            "INSERT INTO files (path, sha256, indexed_at) VALUES (?, ?, ?)",
            (rel_path, _sha256(path), time.time()),
        )
        known_dirs = {
            row[0] for row in conn.execute("SELECT DISTINCT src_dir FROM import_edges")
        }
        known_dirs |= {dir_of(row[0]) for row in conn.execute("SELECT path FROM files")}
        src_dir = dir_of(rel_path)
        for module in imports:
            dst_dir = module_to_dir(module, known_dirs)
            if dst_dir is None or dst_dir == src_dir:
                continue
            conn.execute(
                "INSERT INTO import_edges (src_dir, dst_dir, count) VALUES (?, ?, 1)"
                " ON CONFLICT(src_dir, dst_dir) DO UPDATE SET count = count + 1",
                (src_dir, dst_dir),
            )

    conn.commit()
    conn.close()
