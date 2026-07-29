"""Index building, full and incremental."""

from drift.guard import build, schema


def test_dir_of_handles_nesting_and_root():
    assert build.dir_of("src/db/models.py") == "src/db"
    assert build.dir_of("setup.py") == "."


def test_module_to_dir_maps_known_packages():
    known = {"src/db", "src/api"}

    assert build.module_to_dir("src.db.models", known) == "src/db"
    assert build.module_to_dir("src.db", known) == "src/db"
    assert build.module_to_dir("os.path", known) is None


def test_build_full_indexes_the_sample_repo(sample_repo):
    stats = build.build_full(sample_repo)

    assert stats["files"] == 6
    assert stats["symbols"] >= 7

    conn = schema.connect(sample_repo)
    names = {row[0] for row in conn.execute("SELECT norm_name FROM symbols")}
    assert "validatetoken" in names


def test_build_full_records_observed_import_edges(sample_repo):
    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    edges = {(row[0], row[1]) for row in conn.execute("SELECT src_dir, dst_dir FROM import_edges")}

    assert ("src/services", "src/db") in edges
    assert ("src/api", "src/services") in edges
    # The whole point: this edge does not exist yet.
    assert ("src/api", "src/db") not in edges


def test_update_file_replaces_symbols_for_that_file_only(sample_repo):
    build.build_full(sample_repo)
    target = sample_repo / "src" / "api" / "schemas.py"
    target.write_text("def brand_new_helper(x):\n    return x\n", encoding="utf-8")

    build.update_file(sample_repo, "src/api/schemas.py")

    conn = schema.connect(sample_repo)
    in_file = {
        row[0]
        for row in conn.execute(
            "SELECT norm_name FROM symbols WHERE path = ?", ("src/api/schemas.py",)
        )
    }
    elsewhere = {
        row[0]
        for row in conn.execute(
            "SELECT norm_name FROM symbols WHERE path = ?", ("src/auth/tokens.py",)
        )
    }
    assert in_file == {"brandnewhelper"}
    assert "validatetoken" in elsewhere


def test_a_fresh_index_is_not_stale(sample_repo):
    """A rebuild on every session start would be a regression, not a fix."""
    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)

    assert build.is_stale(sample_repo, conn) is False


def test_one_hand_edit_does_not_trigger_a_rebuild(sample_repo):
    """The user editing a file in their own editor is normal."""
    build.build_full(sample_repo)
    (sample_repo / "src" / "auth" / "tokens.py").write_text(
        "def validate_token(token):\n    return False\n", encoding="utf-8"
    )
    conn = schema.connect(sample_repo)

    assert build.is_stale(sample_repo, conn) is False


def test_a_tree_that_moved_wholesale_is_stale(sample_repo):
    """A checkout or a pull rewrites a large fraction at once."""
    build.build_full(sample_repo)
    for path in sorted(sample_repo.rglob("*.py")):
        path.write_text("def something_else_entirely(a):\n    pass\n", encoding="utf-8")
    conn = schema.connect(sample_repo)

    assert build.is_stale(sample_repo, conn) is True


def test_deleted_files_count_as_movement(sample_repo):
    build.build_full(sample_repo)
    for path in sorted(sample_repo.rglob("*.py")):
        path.unlink()
    conn = schema.connect(sample_repo)

    assert build.is_stale(sample_repo, conn) is True


def test_an_empty_index_is_stale(tmp_path):
    conn = schema.create(tmp_path)
    schema.initialize(conn)

    assert build.is_stale(tmp_path, conn) is True
