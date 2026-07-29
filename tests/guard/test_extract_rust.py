"""Rust: what the matcher finds, and what it refuses to invent."""

from __future__ import annotations

from drift.guard import build, extract, lookup, schema

SAMPLE = """\
use std::collections::HashMap;
use crate::db::client::Pool;
use super::shared::helper;
use crate::api::{routes, schemas};
use self::inner::Thing;

mod inner;

pub fn validate_token(token: &str, audience: &str) -> bool {
    true
}

fn unexported_helper() {}

pub async fn fetch_records() {}

pub struct TokenStore {
    entries: HashMap<String, String>,
}

pub enum Outcome {
    Accepted,
}

pub trait Validator {
    fn validate(&self, token: &str) -> bool;
}

impl TokenStore {
    pub fn new() -> Self {
        Self { entries: HashMap::new() }
    }

    fn internal_detail(&self) {}
}
"""


def _names(source: str) -> list[str]:
    symbols, _ = extract.extract(source, ".rs")
    return [s.name for s in symbols]


def test_it_finds_top_level_declarations():
    names = _names(SAMPLE)

    assert "validate_token" in names
    assert "unexported_helper" in names
    assert "fetch_records" in names
    assert "TokenStore" in names
    assert "Outcome" in names
    assert "Validator" in names


def test_methods_inside_impl_blocks_are_not_indexed():
    """`new`, `fmt` and `from` sit on half the types in any crate."""
    names = _names(SAMPLE)

    assert "new" not in names
    assert "internal_detail" not in names


def test_crate_paths_become_directory_specifiers():
    _, imports = extract.extract(SAMPLE, ".rs")

    assert "db/client/Pool" in imports
    assert "../shared/helper" in imports
    assert "./inner/Thing" in imports


def test_a_braced_use_keeps_its_prefix():
    """`use crate::api::{routes, schemas}` identifies one directory, not two."""
    _, imports = extract.extract("use crate::api::{routes, schemas};\n", ".rs")

    assert imports == ["api"]


def test_external_crates_are_not_places_in_this_repository():
    _, imports = extract.extract("use std::collections::HashMap;\nuse serde::Serialize;\n", ".rs")

    assert imports == []


def test_mod_declarations_are_not_boundary_crossings():
    """`mod inner;` declares a child in the same directory."""
    _, imports = extract.extract("mod inner;\nmod other;\n", ".rs")

    assert imports == []


def test_a_word_inside_a_string_is_not_a_declaration():
    source = 'const MSG: &str = "pub fn not_a_real_function() {}";\n'

    assert _names(source) == []


def _write_rust_repo(root):
    (root / "src" / "auth").mkdir(parents=True)
    (root / "src" / "db").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "auth" / "tokens.rs").write_text(
        "pub fn validate_token(token: &str) -> bool {\n    true\n}\n", encoding="utf-8"
    )
    (root / "src" / "db" / "client.rs").write_text(
        "pub fn open_connection() {}\n", encoding="utf-8"
    )
    (root / "src" / "api" / "routes.rs").write_text(
        "use crate::auth::tokens;\n\npub fn register_routes() {}\n", encoding="utf-8"
    )


def test_a_rust_repository_reports_a_duplicate(tmp_path):
    _write_rust_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract("pub fn validate_token(t: &str) -> bool {\n    false\n}\n", ".rs")
    hits = lookup.find_duplicates(conn, "src/api/schemas.rs", symbols)

    assert hits
    assert "src/auth/tokens.rs:1" in hits[0].message


def test_a_rust_repository_reports_a_first_ever_boundary(tmp_path):
    _write_rust_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    hits = lookup.find_novel_edges(conn, "src/api/routes.rs", ["db/client"])

    assert hits, "src/api has never imported from src/db"
    assert "src/api" in hits[0].message and "src/db" in hits[0].message


def test_an_established_rust_edge_is_not_reported(tmp_path):
    _write_rust_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    assert lookup.find_novel_edges(conn, "src/api/routes.rs", ["auth/tokens"]) == []
