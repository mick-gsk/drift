"""AST extraction of symbols and import targets."""

from drift.guard import extract


def test_normalize_strips_case_and_underscores():
    assert extract.normalize("validate_token") == "validatetoken"
    assert extract.normalize("validateToken") == "validatetoken"
    assert extract.normalize("_private_helper") == "privatehelper"


def test_extract_finds_module_level_functions():
    symbols, _ = extract.extract("def validate_token(token, audience):\n    return True\n")

    assert len(symbols) == 1
    assert symbols[0].name == "validate_token"
    assert symbols[0].norm_name == "validatetoken"
    assert symbols[0].kind == "function"
    assert symbols[0].line == 1


def test_extract_finds_classes():
    symbols, _ = extract.extract("class UserService:\n    pass\n")

    assert symbols[0].kind == "class"
    assert symbols[0].norm_name == "userservice"


def test_extract_ignores_methods_inside_classes():
    source = "class A:\n    def run(self):\n        return 1\n"
    symbols, _ = extract.extract(source)

    assert [s.name for s in symbols] == ["A"]


def test_signature_hash_is_order_insensitive_but_name_sensitive():
    a = extract.signature_hash("function", ["token", "audience"])
    b = extract.signature_hash("function", ["audience", "token"])
    c = extract.signature_hash("function", ["token", "issuer"])

    assert a == b
    assert a != c


def test_extract_collects_import_targets():
    source = "import os\nfrom src.db import models\nfrom src.db.models import fetch\n"
    _, imports = extract.extract(source)

    assert "os" in imports
    assert "src.db" in imports
    assert "src.db.models" in imports


def test_extract_survives_syntax_errors():
    assert extract.extract("def broken(:\n") == ([], [])


def test_common_names_are_stopwords():
    assert "main" in extract.STOPWORDS
    assert "run" in extract.STOPWORDS
    assert "validatetoken" not in extract.STOPWORDS
