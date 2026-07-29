"""Java and Kotlin: what the matcher finds, and what it refuses to invent."""

from __future__ import annotations

from drift.guard import build, extract, lookup, schema

JAVA = """\
package com.example.auth;

import java.util.Map;
import com.example.db.Client;
import static com.example.util.Helpers.escape;
import com.example.api.*;

@Service
public final class TokenStore implements Validator {

    private Map<String, String> entries;

    public boolean validate(String token) {
        return true;
    }

    private void internalDetail() {}
}

interface Validator {
    boolean validate(String token);
}

enum Outcome {
    ACCEPTED
}

record Pair(String left, String right) {}
"""

KOTLIN = """\
package com.example.auth

import com.example.db.Client

fun validateToken(token: String, audience: String): Boolean = true

private fun unexportedHelper() {}

suspend fun fetchRecords() {}

data class TokenStore(val entries: Map<String, String>) {
    fun validate(token: String): Boolean = true
}

object Registry {
    fun register() {}
}
"""


def _names(source: str, suffix: str) -> list[str]:
    symbols, _ = extract.extract(source, suffix)
    return [s.name for s in symbols]


def test_java_finds_top_level_types():
    names = _names(JAVA, ".java")

    assert "TokenStore" in names
    assert "Validator" in names
    assert "Outcome" in names
    assert "Pair" in names


def test_java_members_are_not_indexed():
    """Members are indented; the column-zero anchor excludes them."""
    names = _names(JAVA, ".java")

    assert "validate" not in names
    assert "internalDetail" not in names


def test_kotlin_top_level_functions_are_definitions():
    names = _names(KOTLIN, ".kt")

    assert "validateToken" in names
    assert "unexportedHelper" in names
    assert "fetchRecords" in names
    assert "TokenStore" in names
    assert "Registry" in names


def test_kotlin_members_are_not_indexed():
    names = _names(KOTLIN, ".kt")

    assert "validate" not in names
    assert "register" not in names


def test_imports_carry_the_package_not_the_type():
    """`com.example.db.Client` names the type; `com/example/db` is the place."""
    _, imports = extract.extract(JAVA, ".java")

    assert "com/example/db" in imports
    assert "java/util" in imports
    assert "com/example/util/Helpers" in imports, "a static import ends at the class"
    assert "com/example/api" in imports, "a wildcard import still names its package"


def test_a_word_inside_a_string_is_not_a_declaration():
    source = 'package a;\n\nclass Real { String s = "public class NotReal {}"; }\n'

    assert _names(source, ".java") == ["Real"]


def _write_java_repo(root):
    base = root / "src" / "main" / "java" / "com" / "example"
    (base / "auth").mkdir(parents=True)
    (base / "db").mkdir(parents=True)
    (base / "api").mkdir(parents=True)
    (root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
    (base / "auth" / "TokenStore.java").write_text(
        "package com.example.auth;\n\npublic class TokenStore {}\n", encoding="utf-8"
    )
    (base / "db" / "Client.java").write_text(
        "package com.example.db;\n\npublic class Client {}\n", encoding="utf-8"
    )
    (base / "api" / "Routes.java").write_text(
        "package com.example.api;\n\nimport com.example.auth.TokenStore;\n\n"
        "public class Routes {}\n",
        encoding="utf-8",
    )


def test_a_java_repository_reports_a_duplicate(tmp_path):
    _write_java_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract(
        "package com.example.api;\n\npublic class TokenStore {}\n", ".java"
    )
    hits = lookup.find_duplicates(conn, "src/main/java/com/example/api/TokenStore.java", symbols)

    assert hits
    assert "auth/TokenStore.java" in hits[0].message


def test_a_java_repository_reports_a_first_ever_boundary(tmp_path):
    _write_java_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    hits = lookup.find_novel_edges(
        conn, "src/main/java/com/example/api/Routes.java", ["com/example/db"]
    )

    assert hits, "the api package has never imported from db"
    assert "api" in hits[0].message and "db" in hits[0].message


def test_an_established_java_edge_is_not_reported(tmp_path):
    _write_java_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    assert (
        lookup.find_novel_edges(
            conn, "src/main/java/com/example/api/Routes.java", ["com/example/auth"]
        )
        == []
    )
