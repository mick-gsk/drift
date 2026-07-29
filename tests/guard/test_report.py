"""Guard output formatting and the session counter."""

from drift.guard import lookup, report


def test_no_hits_produces_no_output():
    assert report.format_hits([]) == ""


def test_hits_are_prefixed_and_bounded():
    hits = [
        lookup.Hit("duplicate", "`validate_token` already exists in src/auth/tokens.py:4"),
        lookup.Hit("boundary", "first import from src/api/ into src/db/"),
    ]

    text = report.format_hits(hits)

    assert text.startswith("drift:")
    assert "validate_token" in text
    assert "src/db/" in text
    assert len(text) <= report.MAX_MESSAGE_CHARS


def test_long_hit_lists_are_truncated():
    hits = [lookup.Hit("duplicate", "x" * 200) for _ in range(10)]

    assert len(report.format_hits(hits)) <= report.MAX_MESSAGE_CHARS


def test_counter_starts_at_zero(tmp_path):
    assert report.read_counter(tmp_path) == {"duplicate": 0, "boundary": 0}


def test_bump_accumulates_per_kind(tmp_path):
    report.bump(tmp_path, "duplicate")
    report.bump(tmp_path, "duplicate")
    report.bump(tmp_path, "boundary")

    assert report.read_counter(tmp_path) == {"duplicate": 2, "boundary": 1}


def test_reset_clears_the_counter(tmp_path):
    report.bump(tmp_path, "duplicate")
    report.reset_counter(tmp_path)

    assert report.read_counter(tmp_path) == {"duplicate": 0, "boundary": 0}


def test_summary_line_states_zero_honestly():
    assert "0" in report.summary_line({"duplicate": 0, "boundary": 0})


def test_summary_line_reports_actual_counts():
    line = report.summary_line({"duplicate": 3, "boundary": 1})

    assert "3" in line and "1" in line
