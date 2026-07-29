"""Index schema lifecycle."""

import pathlib
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


def test_index_stays_out_of_the_analysed_repository(tmp_path, guard_cache_home):
    """The guard fires in every repository the user opens, including borrowed ones.

    Dropping an untracked `.drift/` into each of them puts a directory in front
    of people who never installed drift, so the default lives in the cache.
    """
    index = schema.index_path(tmp_path)

    assert guard_cache_home in index.parents
    assert ".drift" not in index.parts
    assert not (tmp_path / ".drift").exists()


def test_a_repository_can_opt_in_by_creating_dot_drift(tmp_path):
    """An existing `.drift/` is a deliberate choice and wins over the cache."""
    (tmp_path / ".drift").mkdir()

    assert schema.index_path(tmp_path).parts[-2:] == (".drift", "index.db")


def test_two_repositories_do_not_share_a_cache_entry(tmp_path):
    first = tmp_path / "alpha"
    second = tmp_path / "beta"
    first.mkdir()
    second.mkdir()

    assert schema.index_path(first) != schema.index_path(second)


def test_the_counter_lives_beside_the_index(tmp_path):
    """One directory for the guard's state, not two."""
    from drift.guard import report

    assert report.counter_path(tmp_path).parent == schema.index_path(tmp_path).parent


def test_wrong_schema_version_is_not_usable(tmp_path):
    conn = schema.create(tmp_path)
    schema.initialize(conn)
    conn.execute("UPDATE meta SET value = '999' WHERE key = 'schema_version'")

    assert schema.is_usable(conn) is False


def test_empty_database_is_not_usable(tmp_path):
    conn = sqlite3.connect(tmp_path / "bare.db")

    assert schema.is_usable(conn) is False


def test_cache_directory_is_readable_even_for_a_relative_repo(tmp_path, monkeypatch):
    """`--repo .` must not key on an empty name and produce a nameless directory."""
    repo = tmp_path / "my-project"
    repo.mkdir()
    monkeypatch.chdir(repo)

    from_relative = schema.index_path(pathlib.Path("."))
    from_absolute = schema.index_path(repo)

    assert from_relative == from_absolute
    assert from_relative.parent.name.startswith("my-project-")
