"""Tests for Phase 4: negative context export and MCP instructions enrichment."""

from __future__ import annotations

import json
from pathlib import Path

from drift.models import (
    NegativeContext,
    NegativeContextCategory,
    NegativeContextScope,
    Severity,
    SignalType,
)
from drift.negative_context_export import (
    MARKER_BEGIN,
    MARKER_END,
    render_negative_context_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_nc(
    *,
    signal: SignalType = SignalType.BROAD_EXCEPTION_MONOCULTURE,
    category: NegativeContextCategory = NegativeContextCategory.ERROR_HANDLING,
    severity: Severity = Severity.HIGH,
    description: str = "Broad exception catch hides bugs",
    forbidden: str = "except Exception: pass",
    canonical: str = "Use specific exception types",
    files: list[str] | None = None,
    confidence: float = 0.9,
) -> NegativeContext:
    return NegativeContext(
        anti_pattern_id=f"neg-test-{signal.value[:3]}",
        category=category,
        source_signal=signal,
        severity=severity,
        scope=NegativeContextScope.FILE,
        description=description,
        forbidden_pattern=forbidden,
        canonical_alternative=canonical,
        affected_files=files or ["src/app.py"],
        confidence=confidence,
        rationale="Test rationale",
    )


# ---------------------------------------------------------------------------
# render_negative_context_markdown
# ---------------------------------------------------------------------------


class TestRenderInstructionsFormat:
    """Tests for 'instructions' output format."""

    def test_contains_yaml_frontmatter(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert md.startswith("---\n")
        assert 'applyTo: "**"' in md

    def test_contains_markers(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert MARKER_BEGIN in md
        assert MARKER_END in md

    def test_contains_do_not_line(self) -> None:
        items = [_make_nc(forbidden="except Exception: pass")]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert "**DO NOT:** except Exception: pass" in md

    def test_contains_instead_line(self) -> None:
        items = [_make_nc(canonical="Use specific exception types")]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert "**INSTEAD:** Use specific exception types" in md

    def test_contains_affected_files(self) -> None:
        items = [_make_nc(files=["src/app.py", "src/utils.py"])]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert "`src/app.py`" in md
        assert "`src/utils.py`" in md

    def test_drift_score_in_footer(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(
            items, fmt="instructions", drift_score=0.42, severity=Severity.MEDIUM,
        )
        assert "0.42" in md
        assert "medium" in md


class TestRenderPromptFormat:
    """Tests for 'prompt' output format."""

    def test_prompt_has_mode_agent(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(items, fmt="prompt")
        assert "mode: agent" in md

    def test_prompt_has_markers(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(items, fmt="prompt")
        assert MARKER_BEGIN in md
        assert MARKER_END in md

    def test_prompt_uses_compact_rules(self) -> None:
        items = [_make_nc()]
        md = render_negative_context_markdown(items, fmt="prompt")
        assert "DO_NOT -> INSTEAD" in md
        assert "[HIGH|" in md
        assert "except Exception: pass -> Use specific exception types" in md
        assert "**DO NOT:**" not in md
        assert "Affected:" not in md


class TestRenderRawFormat:
    """Tests for 'raw' output format."""

    def test_raw_is_valid_json(self) -> None:
        items = [_make_nc()]
        raw = render_negative_context_markdown(items, fmt="raw")
        data = json.loads(raw)
        assert data["format"] == "drift-negative-context-v1"
        assert data["total_items"] == 1
        assert data["items"][0]["signal"] == SignalType.BROAD_EXCEPTION_MONOCULTURE.value

    def test_raw_has_no_markers(self) -> None:
        items = [_make_nc()]
        raw = render_negative_context_markdown(items, fmt="raw")
        assert MARKER_BEGIN not in raw
        assert MARKER_END not in raw


class TestRenderGrouping:
    """Tests for category grouping."""

    def test_security_comes_first(self) -> None:
        items = [
            _make_nc(
                category=NegativeContextCategory.TESTING,
                signal=SignalType.TEST_POLARITY_DEFICIT,
                description="Testing issue",
            ),
            _make_nc(
                category=NegativeContextCategory.SECURITY,
                signal=SignalType.HARDCODED_SECRET,
                description="Security issue",
            ),
        ]
        md = render_negative_context_markdown(items, fmt="instructions")
        sec_pos = md.find("Security Anti-Patterns")
        test_pos = md.find("Testing Anti-Patterns")
        assert sec_pos < test_pos

    def test_multiple_items_in_same_category(self) -> None:
        items = [
            _make_nc(description="Issue A"),
            _make_nc(description="Issue B"),
        ]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert "Issue A" in md
        assert "Issue B" in md


class TestRenderEmpty:
    """Tests for empty state rendering."""

    def test_empty_instructions_format(self) -> None:
        md = render_negative_context_markdown([], fmt="instructions")
        assert "No significant anti-patterns detected" in md
        assert 'applyTo: "**"' in md

    def test_empty_prompt_format(self) -> None:
        md = render_negative_context_markdown([], fmt="prompt")
        assert "No significant anti-patterns detected" in md
        assert "mode: agent" in md

    def test_empty_raw_format(self) -> None:
        raw = render_negative_context_markdown([], fmt="raw")
        data = json.loads(raw)
        assert data["format"] == "drift-negative-context-v1"
        assert data["total_items"] == 0
        assert data["items"] == []


class TestAffectedFileTruncation:
    """Tests for file list truncation at 5 items."""

    def test_more_than_five_files_truncated(self) -> None:
        files = [f"src/mod{i}.py" for i in range(8)]
        items = [_make_nc(files=files)]
        md = render_negative_context_markdown(items, fmt="instructions")
        assert "(+3 more)" in md
        assert "`src/mod0.py`" in md
        assert "`src/mod4.py`" in md
        # 6th file should not be shown inline
        assert "`src/mod5.py`" not in md


# ---------------------------------------------------------------------------
# MCP instructions enrichment
# ---------------------------------------------------------------------------


class TestMCPInstructionsEnrichment:
    """Tests for _load_negative_context_instructions."""

    def test_base_instructions_without_file(self, tmp_path: Path) -> None:
        """Without .drift-negative-context.md, returns base instructions."""
        import os
        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            from drift.mcp_server import (
                _BASE_INSTRUCTIONS,
                _load_negative_context_instructions,
            )
            result = _load_negative_context_instructions()
            assert result == _BASE_INSTRUCTIONS
        finally:
            os.chdir(original)

    def test_enriched_with_do_not_lines(self, tmp_path: Path) -> None:
        """With .drift-negative-context.md, includes DO NOT items."""
        import os

        ctx = tmp_path / ".drift-negative-context.md"
        ctx.write_text(
            f"{MARKER_BEGIN}\n"
            "## Security Anti-Patterns\n\n"
            "- **DO NOT:** Use bare except Exception: pass\n"
            "- **INSTEAD:** Catch specific exceptions\n"
            "- **DO NOT:** Hardcode API keys in source\n"
            "- **INSTEAD:** Use environment variables\n"
            f"\n{MARKER_END}\n",
            encoding="utf-8",
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            from drift.mcp_server import _load_negative_context_instructions
            result = _load_negative_context_instructions()
            assert "KNOWN ANTI-PATTERNS" in result
            assert "Use bare except Exception: pass" in result
            assert "Hardcode API keys in source" in result
        finally:
            os.chdir(original)

    def test_no_markers_returns_base(self, tmp_path: Path) -> None:
        """File without markers returns base instructions."""
        import os

        ctx = tmp_path / ".drift-negative-context.md"
        ctx.write_text("# Some random file\nNo markers here.", encoding="utf-8")

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            from drift.mcp_server import (
                _BASE_INSTRUCTIONS,
                _load_negative_context_instructions,
            )
            result = _load_negative_context_instructions()
            assert result == _BASE_INSTRUCTIONS
        finally:
            os.chdir(original)

    def test_max_ten_do_not_lines(self, tmp_path: Path) -> None:
        """At most 10 DO NOT lines are included."""
        import os

        lines = [f"- **DO NOT:** anti-pattern-{i}\n" for i in range(15)]
        ctx = tmp_path / ".drift-negative-context.md"
        ctx.write_text(
            f"{MARKER_BEGIN}\n{''.join(lines)}{MARKER_END}\n",
            encoding="utf-8",
        )

        original = os.getcwd()
        try:
            os.chdir(tmp_path)
            from drift.mcp_server import _load_negative_context_instructions
            result = _load_negative_context_instructions()
            assert "anti-pattern-9" in result
            assert "anti-pattern-10" not in result
            assert "... and 5 more" in result
        finally:
            os.chdir(original)


# ---------------------------------------------------------------------------
# CLI command registration
# ---------------------------------------------------------------------------


class TestExportContextCLI:
    """Tests for the export-context CLI command."""

    def test_command_registered(self) -> None:
        """export-context is accessible through the CLI group."""
        from click import Context

        from drift.cli import main

        ctx = Context(main)
        commands = main.list_commands(ctx)
        assert "export-context" in commands

    def test_help_text(self) -> None:
        """Command has proper help text."""
        from click.testing import CliRunner

        from drift.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["export-context", "--help"])
        assert result.exit_code == 0
        assert "anti-pattern" in result.output.lower()
