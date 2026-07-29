"""SQLite index: schema, connection handling, and usability checks."""

from __future__ import annotations

import hashlib
import os
import pathlib
import sqlite3

#: 2 added `files.package_root`. A symbol in one package of a workspace does
#: not duplicate a symbol in another, and the guard could not tell before.
#: 3 attributed import edges to the file that declares them. As an aggregate
#: they could only ever grow: removing the last import that created an edge
#: left the row behind, and the boundary signal went permanently silent for a
#: crossing that had become novel again.
SCHEMA_VERSION = 3

_TABLES = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS files (
    path         TEXT PRIMARY KEY,
    sha256       TEXT NOT NULL,
    indexed_at   REAL NOT NULL,
    package_root TEXT NOT NULL DEFAULT '.'
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
    path    TEXT NOT NULL,
    src_dir TEXT NOT NULL,
    dst_dir TEXT NOT NULL,
    PRIMARY KEY (path, src_dir, dst_dir)
);
CREATE INDEX IF NOT EXISTS idx_edges_src ON import_edges(src_dir);
CREATE INDEX IF NOT EXISTS idx_symbols_norm ON symbols(norm_name);
CREATE INDEX IF NOT EXISTS idx_symbols_sig  ON symbols(sig_hash);
CREATE INDEX IF NOT EXISTS idx_symbols_path ON symbols(path);
"""


def state_dir(repo_root: pathlib.Path) -> pathlib.Path:
    """Where the guard keeps its index and tally for one repository.

    The guard is installed once and then fires in every repository the user
    opens, including ones they do not own. Writing `.drift/` into each of them
    would put an untracked directory in front of people who never asked for it
    and never installed drift — a good way to get the plugin uninstalled. So
    the default lives in the user's cache, keyed by the repository path.

    A repository that *wants* the index alongside its source opts in simply by
    having a `.drift/` directory; that path then wins. `DRIFT_CACHE_HOME`
    overrides everything, which is what the tests use to stay off the real
    cache.
    """
    repo_root = pathlib.Path(repo_root)
    local = repo_root / ".drift"
    if local.is_dir():
        return local

    override = os.environ.get("DRIFT_CACHE_HOME")
    if override:
        cache_root = pathlib.Path(override)
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        cache_root = pathlib.Path(xdg) if xdg else pathlib.Path.home() / ".cache"
        cache_root = cache_root / "drift"

    # The digest keys the directory; the name is only there to make the cache
    # readable when someone goes looking. Both come from the resolved path, or
    # `--repo .` would key on "" and produce a nameless directory.
    resolved = repo_root.resolve()
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:16]
    return cache_root / f"{resolved.name or 'repo'}-{digest}"


def index_path(repo_root: pathlib.Path) -> pathlib.Path:
    """Location of the guard index for a repository."""
    return state_dir(repo_root) / "index.db"


def connect(repo_root: pathlib.Path) -> sqlite3.Connection | None:
    """Open an existing index. Returns None when there is none yet.

    Reading and writing are separate functions because their contracts differ:
    a reader must cope with a missing index (the guard stays silent), a writer
    creates one and therefore always gets a connection. Folding both into a
    `create=` flag made every writer look like it could fail when it cannot.
    """
    if not index_path(repo_root).exists():
        return None
    return _open(index_path(repo_root))


def create(repo_root: pathlib.Path) -> sqlite3.Connection:
    """Open the index, creating the file when it does not exist yet."""
    path = index_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    return _open(path)


def _open(path: pathlib.Path) -> sqlite3.Connection:
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
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    except sqlite3.DatabaseError:
        return False
    return bool(row) and row[0] == str(SCHEMA_VERSION)
