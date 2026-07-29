"""SQLite index: schema, connection handling, and usability checks."""

from __future__ import annotations

import pathlib
import sqlite3

SCHEMA_VERSION = 1

_TABLES = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    path       TEXT PRIMARY KEY,
    sha256     TEXT NOT NULL,
    indexed_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols (
    path      TEXT NOT NULL,
    name      TEXT NOT NULL,
    norm_name TEXT NOT NULL,
    kind      TEXT NOT NULL,
    sig_hash  TEXT NOT NULL,
    line      INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS import_edges (
    src_dir TEXT NOT NULL,
    dst_dir TEXT NOT NULL,
    count   INTEGER NOT NULL,
    PRIMARY KEY (src_dir, dst_dir)
);
CREATE INDEX IF NOT EXISTS idx_symbols_norm ON symbols(norm_name);
CREATE INDEX IF NOT EXISTS idx_symbols_sig  ON symbols(sig_hash);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
"""


def index_path(repo_root: pathlib.Path) -> pathlib.Path:
    """Location of the guard index for a repository."""
    return pathlib.Path(repo_root) / ".drift" / "index.db"


def connect(repo_root: pathlib.Path, create: bool = False) -> sqlite3.Connection | None:
    """Open the index. Returns None when it does not exist and create is False."""
    path = index_path(repo_root)
    if not path.exists():
        if not create:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    """Create tables and stamp the schema version."""
    conn.executescript(_TABLES)
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def is_usable(conn: sqlite3.Connection) -> bool:
    """True when the index carries exactly the schema version we understand."""
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return False
    return bool(row) and row[0] == str(SCHEMA_VERSION)
