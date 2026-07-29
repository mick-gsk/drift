"""C#: what the matcher finds, and what it refuses to invent."""

from __future__ import annotations

from drift.guard import build, extract, lookup, schema

BLOCK_SCOPED = """\
using System.Text;
using MyApp.Db;
using static MyApp.Util.Helpers;
using Alias = MyApp.Legacy;

namespace MyApp.Auth
{
    [Service]
    public sealed class TokenStore : IValidator
    {
        public bool Validate(string token)
        {
            return true;
        }

        private void InternalDetail() { }
    }

    public interface IValidator
    {
        bool Validate(string token);
    }

    public enum Outcome
    {
        Accepted
    }
}
"""

FILE_SCOPED = """\
using MyApp.Db;

namespace MyApp.Auth;

public record TokenPair(string Left, string Right);

public struct Marker { }
"""


def _names(source: str) -> list[str]:
    symbols, _ = extract.extract(source, ".cs")
    return [s.name for s in symbols]


def test_types_nested_in_a_namespace_block_are_found():
    """C# indents everything by one level, which no other language here does."""
    names = _names(BLOCK_SCOPED)

    assert "TokenStore" in names
    assert "IValidator" in names
    assert "Outcome" in names


def test_the_file_scoped_namespace_form_is_found():
    names = _names(FILE_SCOPED)

    assert "TokenPair" in names
    assert "Marker" in names


def test_members_are_not_indexed():
    names = _names(BLOCK_SCOPED)

    assert "Validate" not in names
    assert "InternalDetail" not in names


def test_usings_become_directory_paths():
    _, imports = extract.extract(BLOCK_SCOPED, ".cs")

    assert "MyApp/Db" in imports
    assert "System/Text" in imports
    assert "MyApp/Util/Helpers" in imports, "a static using ends at the class"


def test_an_alias_is_not_a_dependency_on_a_place():
    """`using Alias = MyApp.Legacy;` renames rather than reaches."""
    _, imports = extract.extract("using Alias = MyApp.Legacy;\n", ".cs")

    assert imports == []


def test_a_word_inside_a_string_is_not_a_declaration():
    source = 'namespace A;\n\npublic class Real { string s = "public class NotReal {}"; }\n'

    assert _names(source) == ["Real"]


def _write_csharp_repo(root):
    (root / "src" / "MyApp" / "Auth").mkdir(parents=True)
    (root / "src" / "MyApp" / "Db").mkdir(parents=True)
    (root / "src" / "MyApp" / "Api").mkdir(parents=True)
    (root / "src" / "MyApp" / "MyApp.csproj").write_text("<Project/>\n", encoding="utf-8")
    (root / "src" / "MyApp" / "Auth" / "TokenStore.cs").write_text(
        "namespace MyApp.Auth;\n\npublic class TokenStore { }\n", encoding="utf-8"
    )
    (root / "src" / "MyApp" / "Db" / "Client.cs").write_text(
        "namespace MyApp.Db;\n\npublic class Client { }\n", encoding="utf-8"
    )
    (root / "src" / "MyApp" / "Api" / "Routes.cs").write_text(
        "using MyApp.Auth;\n\nnamespace MyApp.Api;\n\npublic class Routes { }\n",
        encoding="utf-8",
    )


def test_a_csharp_repository_reports_a_duplicate(tmp_path):
    _write_csharp_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    symbols, _ = extract.extract("namespace MyApp.Api;\n\npublic class TokenStore { }\n", ".cs")
    hits = lookup.find_duplicates(conn, "src/MyApp/Api/TokenStore.cs", symbols)

    assert hits
    assert "Auth/TokenStore.cs" in hits[0].message


def test_a_csharp_repository_reports_a_first_ever_boundary(tmp_path):
    _write_csharp_repo(tmp_path)
    build.build_full(tmp_path)
    conn = schema.connect(tmp_path)

    hits = lookup.find_novel_edges(conn, "src/MyApp/Api/Routes.cs", ["MyApp/Db"])

    assert hits, "Api has never used Db"
    assert "Api" in hits[0].message and "Db" in hits[0].message


def test_a_csproj_marks_a_package(tmp_path):
    """The marker name varies per project, so the directory has to be searched."""
    (tmp_path / "src" / "Thing").mkdir(parents=True)
    (tmp_path / "src" / "Thing" / "Thing.csproj").write_text("<Project/>\n", encoding="utf-8")

    assert build.package_root_of(tmp_path, "src/Thing/Model.cs", {}) == "src/Thing"
