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


def test_package_root_finds_the_nearest_marker(tmp_path):
    (tmp_path / "crates" / "cli" / "src").mkdir(parents=True)
    (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
    (tmp_path / "crates" / "cli" / "Cargo.toml").write_text("[package]\n", encoding="utf-8")

    assert build.package_root_of(tmp_path, "crates/cli/src/main.rs", {}) == "crates/cli"
    assert build.package_root_of(tmp_path, "build.rs", {}) == "."


def test_a_repository_without_markers_is_one_package(tmp_path):
    (tmp_path / "src").mkdir()

    assert build.package_root_of(tmp_path, "src/thing.py", {}) == "."


def test_staleness_sample_spans_a_medium_sized_index(tmp_path):
    files = []
    for index in range(39):
        path = tmp_path / f"file_{index:02d}.py"
        path.write_text(f"def value_{index}():\n    return {index}\n", encoding="utf-8")
        files.append(path)
    build.build_full(tmp_path)

    for path in files[20:]:
        path.write_text("def branch_version():\n    return False\n", encoding="utf-8")
    conn = schema.connect(tmp_path)

    assert build.is_stale(tmp_path, conn) is True


def test_re_indexing_a_file_does_not_multiply_its_edges(sample_repo):
    """Five re-indexings of one unchanged file took a count from 2 to 12."""
    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    before = conn.execute("SELECT COUNT(*) FROM import_edges").fetchone()[0]
    conn.close()

    for _ in range(5):
        build.update_file(sample_repo, "src/api/routes.py")

    conn = schema.connect(sample_repo)
    assert conn.execute("SELECT COUNT(*) FROM import_edges").fetchone()[0] == before
    conn.close()


def test_removing_an_import_removes_its_edge(sample_repo):
    """A crossing that stopped existing has to become novel again.

    As an aggregate the row survived its last declaring import, so the guard
    went permanently silent about a boundary it should announce.
    """
    from drift.guard import lookup

    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "routes.py").write_text(
        "def register():\n    pass\n", encoding="utf-8"
    )
    build.update_file(sample_repo, "src/api/routes.py")

    conn = schema.connect(sample_repo)
    hits = lookup.find_novel_edges(conn, "src/api/routes.py", ["src.services.user_service"])
    conn.close()

    assert hits, "the edge outlived the import that created it"


def test_nested_repositories_are_not_this_repository(sample_repo):
    """A worktree, submodule or vendored clone is somebody else's source.

    Measured on drift itself: 1041 of 2169 indexed files — 48 % — were copies
    of the repository under `.claude/worktrees/`, and the build took 5400 ms
    instead of 4216 ms. Anything that enumerates the index rather than
    answering one per-edit question then sees every finding twice. See #797.

    A nested `.git` is what worktrees, submodules and vendored clones have in
    common, so one rule covers all three instead of a list of names guessed in
    advance. Worktrees mark themselves with a `.git` file, clones with a
    directory; both count.
    """
    nested = sample_repo / "vendored" / "otherlib"
    (nested / ".git").mkdir(parents=True)
    (nested / "copy.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )
    worktree = sample_repo / ".worktrees" / "wip"
    worktree.mkdir(parents=True)
    (worktree / ".git").write_text("gitdir: ../../.git/worktrees/wip\n", encoding="utf-8")
    (worktree / "copy.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )

    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    paths = {row[0] for row in conn.execute("SELECT path FROM files")}

    assert not [p for p in paths if p.startswith("vendored/")], sorted(paths)
    assert not [p for p in paths if p.startswith(".worktrees/")], sorted(paths)
    assert "src/auth/tokens.py" in paths, "the repository's own source still indexes"


def test_language_specific_build_output_is_skipped(sample_repo):
    """The skip list has to keep up with the languages the guard reads.

    It covered Python and npm while the guard grew into Go, Rust, the JVM and
    C#. Their build output is code nobody in this repository wrote or edits.
    """
    for directory in ("vendor", "target", "obj", ".claude"):
        out = sample_repo / directory / "pkg"
        out.mkdir(parents=True)
        (out / "generated.py").write_text("def widget_maker():\n    pass\n", encoding="utf-8")

    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    paths = {row[0] for row in conn.execute("SELECT path FROM files")}

    assert not [p for p in paths if "generated.py" in p], sorted(paths)


def test_a_copied_tree_does_not_silence_the_guard(sample_repo):
    """The consequence #797 is actually about, asserted end to end.

    A copy that carries its own manifest is already harmless: `_first_real_match`
    filters candidates by package root before it counts them, so such a copy was
    never a candidate. A copy *without* one — a `cp -r`, a backup directory, a
    worktree of a project whose root has no manifest — inherits the parent's
    package root and does count. Three of those plus the original is four
    definitions, one above the ceiling at which a repeated name stops being
    reported, and the duplicate the guard exists to catch disappears.

    Verified against pristine `origin/main` before this fix: 4 files indexed,
    duplicate reported False. With the fix: 1 file indexed, reported True.
    """
    from drift.guard import extract, lookup

    for i in range(3):
        copy = sample_repo / ".worktrees" / f"wt{i}" / "src" / "auth"
        copy.mkdir(parents=True)
        (sample_repo / ".worktrees" / f"wt{i}" / ".git").write_text("gitdir: x\n", encoding="utf-8")
        (copy / "tokens.py").write_text(
            "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
        )

    build.build_full(sample_repo)
    conn = schema.connect(sample_repo)
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n", ".py")

    hits = lookup.find_duplicates(conn, "src/api/schemas.py", symbols)

    assert hits, "the guard must still report the duplicate it was built to catch"
