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
