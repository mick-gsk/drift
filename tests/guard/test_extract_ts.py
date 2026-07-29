"""TypeScript and JavaScript: what the matcher finds, and what it refuses to invent."""

from __future__ import annotations

from drift.guard import build, extract, lookup, report, schema

SAMPLE = """\
import { pool } from '../db/client';
import React from 'react';
import type { User } from './types';

export async function validateToken(token: string, audience: string) {
  return true;
}

function localHelper() {}

export class TokenStore {
  validate() { return true; }
  private helper() {}
}

export interface Session {
  id: string;
}

export const DEFAULT_TTL = 3600;

const lazy = () => import('./heavy');
const legacy = require('../legacy/shim');
"""


def _names(source: str, suffix: str = ".ts") -> list[str]:
    symbols, _ = extract.extract(source, suffix)
    return [s.name for s in symbols]


def test_it_finds_top_level_declarations():
    names = _names(SAMPLE)

    assert "validateToken" in names
    assert "localHelper" in names
    assert "TokenStore" in names
    assert "Session" in names
    assert "lazy" in names, "an arrow function is a definition"


def test_plain_constants_are_not_definitions():
    """Python indexes `def` and `class`, not module-level assignments.

    Indexing every TypeScript `const` broke that symmetry and was the largest
    single source of noise measured against real repositories: `config`,
    `version` and `ignorePattern` collide across unrelated files and say
    nothing. A binding counts only when it holds a function.
    """
    names = _names(SAMPLE)

    assert "DEFAULT_TTL" not in names


def test_it_ignores_class_members():
    """Same rule as Python: methods repeat everywhere and would drown the signal."""
    names = _names(SAMPLE)

    assert "validate" not in names
    assert "helper" not in names


def test_it_collects_every_import_shape():
    _, imports = extract.extract(SAMPLE, ".ts")

    assert "../db/client" in imports
    assert "./types" in imports
    assert "react" in imports
    assert "./heavy" in imports, "dynamic import() is a real dependency"
    assert "../legacy/shim" in imports, "require() is a real dependency"


def test_camel_case_and_snake_case_collide():
    """`validateToken` in TypeScript must match `validate_token` in Python."""
    ts_symbols, _ = extract.extract("export function validateToken(a) {}\n", ".ts")
    py_symbols, _ = extract.extract("def validate_token(a):\n    pass\n", ".py")

    assert ts_symbols[0].norm_name == py_symbols[0].norm_name


def test_an_unsupported_suffix_yields_nothing():
    """A file type stays silent until it is supported on purpose.

    The suffix is deliberately fictional. Naming a real unsupported language
    here made this test fail twice, once when Go arrived and once for Rust —
    which is the correct behaviour reported as a failure.
    """
    assert extract.extract("func main() {}\n", ".madeuplang") == ([], [])


def test_line_numbers_point_at_the_declaration():
    symbols, _ = extract.extract(SAMPLE, ".ts")
    by_name = {s.name: s.line for s in symbols}

    assert SAMPLE.split("\n")[by_name["validateToken"] - 1].startswith("export async function")
    assert SAMPLE.split("\n")[by_name["TokenStore"] - 1].startswith("export class")


def test_a_word_inside_a_string_is_not_a_declaration():
    """Anchoring to column zero and a keyword is what keeps this honest."""
    source = 'const message = "export function notARealFunction() {}";\n'

    assert _names(source) == []


def test_indented_declarations_are_not_top_level():
    source = "function outer() {\n  function inner() {}\n  class Inner {}\n}\n"

    assert _names(source) == ["outer"]


def test_relative_imports_resolve_onto_directories():
    known = {"src/api", "src/db", "src/auth", "."}

    assert build.import_to_dir("../db/client", "src/api", known) == "src/db"
    assert build.import_to_dir("../db", "src/api", known) == "src/db"
    assert build.import_to_dir("./helpers", "src/api", known) == "src/api"


def test_package_specifiers_are_not_repository_directories():
    known = {"src/api", "react", "."}

    assert build.import_to_dir("@scope/pkg", "src/api", known) is None
    assert build.import_to_dir("lodash/fp", "src/api", known) is None


def _write_ts_repo(root):
    (root / "src" / "auth").mkdir(parents=True)
    (root / "src" / "api").mkdir(parents=True)
    (root / "src" / "db").mkdir(parents=True)
    (root / "src" / "auth" / "tokens.ts").write_text(
        "export function validateToken(token: string) {\n  return true;\n}\n", encoding="utf-8"
    )
    (root / "src" / "api" / "routes.ts").write_text(
        "import { validateToken } from '../auth/tokens';\nexport function register() {}\n",
        encoding="utf-8",
    )
    (root / "src" / "db" / "client.ts").write_text("export const pool = 1;\n", encoding="utf-8")


def test_a_typescript_repository_reports_a_duplicate(tmp_path):
    _write_ts_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract(
        "export function validateToken(t: string) {\n  return false;\n}\n", ".ts"
    )
    hits = lookup.find_duplicates(conn, "src/api/schemas.ts", symbols)

    assert hits, "a duplicated TypeScript export must be reported"
    assert "src/auth/tokens.ts:1" in hits[0].message


def test_a_typescript_repository_reports_a_first_ever_boundary(tmp_path):
    _write_ts_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    hits = lookup.find_novel_edges(conn, "src/api/routes.ts", ["../db/client"])

    assert hits, "src/api has never imported from src/db"
    assert "src/api" in hits[0].message and "src/db" in hits[0].message


def test_an_established_typescript_edge_is_not_reported(tmp_path):
    """src/api already imports from src/auth, so that crossing is not news."""
    _write_ts_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    assert lookup.find_novel_edges(conn, "src/api/routes.ts", ["../auth/tokens"]) == []


def test_python_and_typescript_share_one_index(tmp_path):
    """A symbol defined in Python must be found from a TypeScript file."""
    _write_ts_repo(tmp_path)
    (tmp_path / "src" / "auth" / "session.py").write_text(
        "def rotate_secret(a):\n    return a\n", encoding="utf-8"
    )
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract("export function rotateSecret(a) {}\n", ".ts")
    hits = lookup.find_duplicates(conn, "src/api/new.ts", symbols)

    assert hits, "the index is one index, not one per language"
    assert "session.py" in hits[0].message
    assert report.format_hits(hits)
