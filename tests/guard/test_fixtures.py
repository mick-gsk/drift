"""The ground-truth corpus must stay well-formed."""


def test_sample_repo_has_all_source_files(sample_repo):
    paths = sorted(str(p.relative_to(sample_repo)) for p in sample_repo.rglob("*.py"))
    assert paths == [
        "src/api/routes.py",
        "src/api/schemas.py",
        "src/auth/session.py",
        "src/auth/tokens.py",
        "src/db/models.py",
        "src/services/user_service.py",
    ]


def test_expected_declares_cases(expected):
    assert len(expected["duplicate_cases"]) >= 2
    assert len(expected["boundary_cases"]) >= 1
    assert len(expected["clean_files"]) >= 3
