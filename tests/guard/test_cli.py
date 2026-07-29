"""The lean guard CLI."""

import json
import subprocess
import sys

from drift.guard import build, report


def _run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, "-m", "drift.guard", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_build_reports_counts(sample_repo):
    result = _run("build", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert json.loads(result.stdout)["files"] == 6


def test_pre_is_silent_for_files_that_already_exist(sample_repo):
    build.build_full(sample_repo)

    result = _run("pre", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_pre_briefs_the_agent_when_a_new_file_is_created(sample_repo):
    build.build_full(sample_repo)

    result = _run("pre", "--repo", str(sample_repo), "--file", "src/api/handlers.py")

    assert result.returncode == 0
    assert "src/services" in result.stdout
    assert "get_user" in result.stdout


def test_reset_clears_the_counter(sample_repo):
    build.build_full(sample_repo)
    report.bump(sample_repo, "boundary")

    result = _run("reset", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert report.read_counter(sample_repo) == {"duplicate": 0, "boundary": 0}


def test_post_reports_a_duplicate_and_bumps_the_counter(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "schemas.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )

    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/schemas.py")

    assert result.returncode == 0
    assert "validate_token" in result.stdout
    assert report.read_counter(sample_repo)["duplicate"] == 1


def test_post_reports_a_novel_boundary_crossing(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "routes.py").write_text(
        "from src.db import models\n\n\ndef get_user(user_id):\n"
        "    return models.fetch_user_row(user_id)\n",
        encoding="utf-8",
    )

    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert "src/db" in result.stdout
    assert report.read_counter(sample_repo)["boundary"] == 1


def test_post_without_an_index_is_silent_and_succeeds(sample_repo):
    result = _run("post", "--repo", str(sample_repo), "--file", "src/api/routes.py")

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_stats_prints_the_summary(sample_repo):
    build.build_full(sample_repo)
    report.bump(sample_repo, "duplicate")

    result = _run("stats", "--repo", str(sample_repo))

    assert "1 duplicate" in result.stdout


def test_doctor_passes_on_a_built_repo(sample_repo):
    build.build_full(sample_repo)

    result = _run("doctor", "--repo", str(sample_repo))

    assert result.returncode == 0
    assert "[x]" in result.stdout


def test_doctor_fails_without_an_index(sample_repo):
    result = _run("doctor", "--repo", str(sample_repo))

    assert result.returncode == 1
    assert "[ ]" in result.stdout
