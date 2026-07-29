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
