"""Guard output formatting and the session counter."""

import json

import pytest

from drift.guard import lookup, report, schema


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


@pytest.fixture
def indexed(tmp_path):
    """A repository with an index, which is where the tally now lives."""
    conn = schema.create(tmp_path)
    schema.initialize(conn)
    conn.close()
    return tmp_path


def test_counter_starts_at_zero(indexed):
    assert report.read_counter(indexed) == {"duplicate": 0, "boundary": 0}


def test_bump_accumulates_per_kind(indexed):
    report.bump(indexed, "duplicate")
    report.bump(indexed, "duplicate")
    report.bump(indexed, "boundary")

    assert report.read_counter(indexed) == {"duplicate": 2, "boundary": 1}


def test_reset_clears_the_counter(indexed):
    report.bump(indexed, "duplicate")
    report.reset_counter(indexed)

    assert report.read_counter(indexed) == {"duplicate": 0, "boundary": 0}


def test_without_an_index_there_is_nothing_to_count(tmp_path):
    """No index means the guard reported nothing, so a tally would be a lie."""
    report.bump(tmp_path, "duplicate")

    assert report.read_counter(tmp_path) == {"duplicate": 0, "boundary": 0}


def test_the_counter_survives_concurrent_hooks(indexed):
    """Claude Code fires PostToolUse concurrently for batched tool calls.

    Read-modify-write on a JSON file lost 194 of 200 increments across eight
    threads. The tally is the one number the user sees, so it has to hold.
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: report.bump(indexed, "duplicate"), range(200)))

    assert report.read_counter(indexed)["duplicate"] == 200


def test_summary_line_states_zero_honestly():
    assert "0" in report.summary_line({"duplicate": 0, "boundary": 0})


def test_summary_line_reports_actual_counts():
    line = report.summary_line({"duplicate": 3, "boundary": 1})

    assert "3" in line and "1" in line


def test_hook_json_puts_agent_text_where_claude_reads_it():
    """Plain stdout never reaches the model — additionalContext is the only path."""
    payload = json.loads(report.hook_json("PostToolUse", agent_text="drift: found it"))

    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert payload["hookSpecificOutput"]["additionalContext"] == "drift: found it"


def test_hook_json_keeps_the_user_channel_separate():
    payload = json.loads(report.hook_json("Stop", user_text="drift: 2 duplicate(s)"))

    assert payload["systemMessage"] == "drift: 2 duplicate(s)"
    assert "hookSpecificOutput" not in payload


def test_hook_json_says_nothing_when_there_is_nothing_to_say():
    assert report.hook_json("PostToolUse") == ""
