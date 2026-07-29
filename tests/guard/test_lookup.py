"""Duplicate and boundary lookups against a built index."""

from drift.guard import build, extract, lookup, schema


def _conn(repo):
    build.build_full(repo)
    return schema.connect(repo)


def test_duplicate_is_reported_across_files(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    hits = lookup.find_duplicates(conn, "src/api/schemas.py", symbols)

    assert len(hits) == 1
    assert hits[0].kind == "duplicate"
    assert "src/auth/tokens.py" in hits[0].message
    assert "validate_token" in hits[0].message


def test_camel_case_rename_still_counts_as_duplicate(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validateToken(a, b):\n    return True\n")

    hits = lookup.find_duplicates(conn, "src/services/user_service.py", symbols)

    assert len(hits) == 1


def test_symbol_in_its_own_file_is_not_a_duplicate(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    assert lookup.find_duplicates(conn, "src/auth/tokens.py", symbols) == []


def test_stopword_names_are_never_duplicates(sample_repo):
    conn = _conn(sample_repo)
    symbols, _ = extract.extract("def run(self):\n    return 1\n")

    assert lookup.find_duplicates(conn, "src/api/schemas.py", symbols) == []


def test_novel_edge_is_reported(sample_repo):
    conn = _conn(sample_repo)

    hits = lookup.find_novel_edges(conn, "src/api/routes.py", ["src.db.models"])

    assert len(hits) == 1
    assert hits[0].kind == "boundary"
    assert "src/api" in hits[0].message and "src/db" in hits[0].message


def test_existing_edge_is_silent(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.find_novel_edges(conn, "src/api/routes.py", ["src.services.user_service"]) == []


def test_stdlib_imports_are_silent(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.find_novel_edges(conn, "src/api/routes.py", ["os", "json.decoder"]) == []


def test_neighbourhood_lists_sibling_symbols(sample_repo):
    conn = _conn(sample_repo)

    names = lookup.neighbourhood(conn, "src/auth/session.py")

    assert "validate_token" in names
    assert "issue_token" in names


def test_known_targets_lists_existing_edges(sample_repo):
    conn = _conn(sample_repo)

    assert lookup.known_targets(conn, "src/api/routes.py") == ["src/services"]


def _index(tmp_path, files: dict[str, str]):
    for rel, source in files.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    build.build_full(tmp_path)
    return schema.connect(tmp_path)


def _hit_names(conn, rel_path, source, suffix=".py"):
    symbols, _ = extract.extract(source, suffix)
    return [h.message for h in lookup.find_duplicates(conn, rel_path, symbols)]


def test_a_function_does_not_duplicate_a_class(tmp_path):
    """`request` and `Request` are different things; saying otherwise looks convincing."""
    conn = _index(tmp_path, {"src/models.py": "class Requestor:\n    pass\n"})

    assert _hit_names(conn, "src/api.py", "def requestor(url):\n    pass\n") == []


def test_a_name_repeated_across_the_codebase_is_a_convention(tmp_path):
    """date-fns implements `formatLong` in 93 locales. The author of the 94th knows."""
    files = {
        f"src/locale/l{i}/format.py": "def format_long(a):\n    pass\n"
        for i in range(lookup.MAX_DUPLICATE_OCCURRENCES + 2)
    }
    conn = _index(tmp_path, files)

    assert _hit_names(conn, "src/locale/new/format.py", "def format_long(a):\n    pass\n") == []


def test_a_name_that_exists_once_elsewhere_is_still_reported(tmp_path):
    """The rare case is the whole point; the cap must not swallow it."""
    conn = _index(tmp_path, {"src/auth/tokens.py": "def validate_token(a):\n    pass\n"})

    assert _hit_names(conn, "src/api/schemas.py", "def validate_token(a):\n    pass\n")


def test_short_names_carry_no_evidence(tmp_path):
    conn = _index(tmp_path, {"src/a.py": "def add(a, b):\n    return a\n"})

    assert _hit_names(conn, "src/b.py", "def add(a, b):\n    return b\n") == []


def test_dunder_names_are_language_protocol(tmp_path):
    conn = _index(tmp_path, {"src/a.py": "def __getattr__(name):\n    pass\n"})

    assert _hit_names(conn, "src/b.py", "def __getattr__(name):\n    pass\n") == []


def test_directories_that_repeat_by_design_are_neither_source_nor_target(tmp_path):
    conn = _index(tmp_path, {"examples/one.py": "def build_widget(a):\n    pass\n"})

    assert _hit_names(conn, "src/real.py", "def build_widget(a):\n    pass\n") == []
    assert _hit_names(conn, "tests/thing.py", "def build_widget(a):\n    pass\n") == []


def test_test_files_are_detected_by_name_as_well_as_directory():
    """pytest puts `test_x.py` under tests/; date-fns puts `test.ts` beside the source."""
    assert lookup.repeats_by_design("src/foo/test.ts")
    assert lookup.repeats_by_design("src/foo/thing.test.ts")
    assert lookup.repeats_by_design("src/foo/thing.spec.ts")
    assert lookup.repeats_by_design("pkg/test_thing.py")
    assert lookup.repeats_by_design("pkg/thing_test.go")
    assert not lookup.repeats_by_design("src/foo/latest.ts")
    assert not lookup.repeats_by_design("src/contest/thing.py")
