"""Index schema lifecycle."""

import sqlite3

from drift.guard import schema


def test_connect_without_index_returns_none(tmp_path):
    assert schema.connect(tmp_path) is None


def test_initialize_creates_all_tables(tmp_path):
    conn = schema.create(tmp_path)
    schema.initialize(conn)

    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "files", "symbols", "import_edges"} <= names
    assert schema.is_usable(conn) is True


def test_index_lands_in_dot_drift(tmp_path):
    assert schema.index_path(tmp_path).parts[-2:] == (".drift", "index.db")


def test_wrong_schema_version_is_not_usable(tmp_path):
    conn = schema.create(tmp_path)
    schema.initialize(conn)
    conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")

    assert schema.is_usable(conn) is False


def test_empty_database_is_not_usable(tmp_path):
    conn = sqlite3.connect(tmp_path / "bare.db")

    assert schema.is_usable(conn) is False
