"""Regression tests for issue #473: PHR findings must use the AI_QUALITY category.

Phantom references detect AI-hallucinated symbol usage. They were previously
exported under the generic COMPLETENESS category, which hid them from
consumers filtering for AI-specific anti-patterns and diverged from the
``ai_quality`` category already used in signal_registry.py.
"""

from __future__ import annotations

from pathlib import Path

from drift.models import (
    Finding,
    NegativeContextCategory,
    Severity,
    SignalType,
)
from drift.negative_context import findings_to_negative_context
from drift.negative_context.core import _SIGNAL_CATEGORY
from drift.negative_context.export import (
    _CATEGORY_HEADING,
    render_negative_context_markdown,
)


def _phr_finding() -> Finding:
    return Finding(
        signal_type=SignalType.PHANTOM_REFERENCE,
        severity=Severity.MEDIUM,
        score=0.7,
        title="2 unresolvable references in api/client.py",
        description="Unresolvable names detected",
        file_path=Path("api/client.py"),
        start_line=10,
        end_line=30,
        metadata={
            "phantom_names": [
                {"name": "fetch_remote_config", "line": 15},
                {"name": "validate_token", "line": 22},
            ],
            "phantom_count": 2,
        },
    )


class TestPhantomReferenceAIQualityCategory:
    def test_phantom_reference_uses_ai_quality_category(self) -> None:
        """The signal-to-category map must classify PHR as AI_QUALITY."""
        assert (
            _SIGNAL_CATEGORY[SignalType.PHANTOM_REFERENCE]
            == NegativeContextCategory.AI_QUALITY
        )

    def test_ai_quality_category_has_export_heading(self) -> None:
        """AI_QUALITY must render under its own section heading."""
        assert (
            _CATEGORY_HEADING[NegativeContextCategory.AI_QUALITY]
            == "AI-Generated Code Anti-Patterns"
        )

    def test_all_categories_have_export_headings(self) -> None:
        """Every category should have an explicit heading so no section
        silently falls back to a title-cased enum value."""
        for category in NegativeContextCategory:
            assert category in _CATEGORY_HEADING

    def test_phr_finding_generates_ai_quality_item(self) -> None:
        """End to end: a PHR finding produces an AI_QUALITY context item."""
        items = findings_to_negative_context([_phr_finding()])
        assert len(items) == 1
        assert items[0].category == NegativeContextCategory.AI_QUALITY
        assert items[0].source_signal == SignalType.PHANTOM_REFERENCE

    def test_phr_item_renders_under_ai_quality_section(self) -> None:
        """End to end: the rendered export places PHR items in the
        AI-Generated Code Anti-Patterns section, not Completeness."""
        items = findings_to_negative_context([_phr_finding()])
        rendered = render_negative_context_markdown(
            items,
            fmt="instructions",
            drift_score=0.4,
            severity=Severity.MEDIUM,
        )
        assert "## AI-Generated Code Anti-Patterns" in rendered
        assert "## Completeness Anti-Patterns" not in rendered
