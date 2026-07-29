"""Go: what the matcher finds, and what it refuses to invent."""

from __future__ import annotations

from drift.guard import build, extract, lookup, schema

SAMPLE = """\
package auth

import (
	"fmt"
	"strings"

	"github.com/org/repo/internal/db"
)

import "os"

// ValidateToken checks a bearer token.
func ValidateToken(token string, audience string) bool {
	return true
}

func unexportedHelper() {}

type TokenStore struct {
	entries map[string]string
}

type Validator interface {
	Validate(token string) bool
}

func (s *TokenStore) Validate(token string) bool {
	return strings.HasPrefix(token, "x")
}

func (s TokenStore) String() string {
	return fmt.Sprint(db.Name)
}
"""


def _names(source: str) -> list[str]:
    symbols, _ = extract.extract(source, ".go")
    return [s.name for s in symbols]


def test_it_finds_package_level_declarations():
    names = _names(SAMPLE)

    assert "ValidateToken" in names
    assert "unexportedHelper" in names
    assert "TokenStore" in names
    assert "Validator" in names


def test_methods_on_receivers_are_not_indexed():
    """`String`, `Error`, `Read` and `Close` sit on every type in a package.

    The issue that scoped this work argued for including them, since a method
    is package-level API in Go. The noise measurement that came before argued
    louder: methods are excluded in Python and TypeScript for exactly this
    reason, and Go's method names repeat harder than either.
    """
    names = _names(SAMPLE)

    assert "Validate" not in names
    assert "String" not in names


def test_it_reads_both_import_forms():
    _, imports = extract.extract(SAMPLE, ".go")

    assert "fmt" in imports
    assert "strings" in imports
    assert "github.com/org/repo/internal/db" in imports
    assert "os" in imports, "the single-line import form is real Go"


def test_a_word_inside_a_string_is_not_a_declaration():
    source = 'package main\n\nvar msg = "func NotARealFunction() {}"\n'

    assert _names(source) == []


def test_indented_declarations_are_not_package_level():
    """gofmt makes column zero an unusually reliable proxy for package level."""
    source = "package main\n\nfunc outer() {\n\tinner := func() {}\n\t_ = inner\n}\n"

    assert _names(source) == ["outer"]


def test_module_paths_resolve_by_their_trailing_segments():
    """The repository knows itself as `internal/db`, not as its module path."""
    known = {"internal/db", "internal/api", "."}

    assert build.suffix_to_dir("github.com/org/repo/internal/db", known) == "internal/db"
    assert build.suffix_to_dir("github.com/other/pkg", known) is None


def test_trailing_segment_matching_is_reserved_for_go():
    """`lodash/fp` must not resolve onto a directory named `fp`; date-fns has one."""
    known = {"src/fp", "fp", "."}

    assert build.import_to_dir("lodash/fp", "src", known, ".ts") is None
    assert build.import_to_dir("github.com/org/repo/fp", "src", known, ".go") == "fp"


def _write_go_repo(root):
    (root / "internal" / "auth").mkdir(parents=True)
    (root / "internal" / "db").mkdir(parents=True)
    (root / "api").mkdir(parents=True)
    (root / "internal" / "auth" / "tokens.go").write_text(
        "package auth\n\nfunc ValidateToken(token string) bool {\n\treturn true\n}\n",
        encoding="utf-8",
    )
    (root / "internal" / "db" / "client.go").write_text(
        "package db\n\nfunc OpenConnection() error {\n\treturn nil\n}\n", encoding="utf-8"
    )
    (root / "api" / "routes.go").write_text(
        'package api\n\nimport "github.com/org/repo/internal/auth"\n\n'
        "func RegisterRoutes() {\n\t_ = auth.ValidateToken\n}\n",
        encoding="utf-8",
    )


def test_a_go_repository_reports_a_duplicate(tmp_path):
    _write_go_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract(
        "package api\n\nfunc ValidateToken(t string) bool {\n\treturn false\n}\n", ".go"
    )
    hits = lookup.find_duplicates(conn, "api/schemas.go", symbols)

    assert hits
    assert "internal/auth/tokens.go:3" in hits[0].message


def test_a_go_repository_reports_a_first_ever_boundary(tmp_path):
    _write_go_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    hits = lookup.find_novel_edges(conn, "api/routes.go", ["github.com/org/repo/internal/db"])

    assert hits, "api has never imported from internal/db"
    assert "api" in hits[0].message and "internal/db" in hits[0].message


def test_an_established_go_edge_is_not_reported(tmp_path):
    _write_go_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    assert (
        lookup.find_novel_edges(conn, "api/routes.go", ["github.com/org/repo/internal/auth"]) == []
    )


def test_go_shares_the_index_with_python_and_typescript(tmp_path):
    _write_go_repo(tmp_path)
    (tmp_path / "internal" / "auth" / "session.py").write_text(
        "def rotate_secret(a):\n    return a\n", encoding="utf-8"
    )
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract("package api\n\nfunc RotateSecret(a string) {}\n", ".go")
    hits = lookup.find_duplicates(conn, "api/new.go", symbols)

    assert hits, "one index, not one per language"
    assert "session.py" in hits[0].message
