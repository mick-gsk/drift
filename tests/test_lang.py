"""Tests for the Translation Layer (drift.lang).

Covers:
- Message catalog completeness (every registered signal has plain templates)
- translate_finding() produces readable output
- Template variable substitution ({file}, {symbol}, etc.)
- Language fallback (unknown language → English)
- Audience modes (developer vs. plain)
- Enrichment function for pipeline integration
"""

from __future__ import annotations

from pathlib import Path

import pytest
from drift.models._enums import Severity
from drift.models._findings import Finding
from drift.signal_registry import get_all_meta

# ---------------------------------------------------------------------------
# Catalog completeness
# ---------------------------------------------------------------------------


class TestCatalogCompleteness:
    """Every registered signal must have a plain-language template."""

    def test_all_signals_have_plain_template(self) -> None:
        from drift.lang._catalog import PLAIN_CATALOG

        all_signal_ids = {m.signal_id for m in get_all_meta()}
        catalog_ids = set(PLAIN_CATALOG.keys())
        missing = all_signal_ids - catalog_ids
        assert not missing, f"Signals without plain template: {missing}"

    def test_every_template_has_required_fields(self) -> None:
        from drift.lang._catalog import PLAIN_CATALOG

        required = {"title", "description", "impact", "action"}
        for signal_id, templates in PLAIN_CATALOG.items():
            for lang, tpl in templates.items():
                for field in required:
                    assert field in tpl, (
                        f"PLAIN_CATALOG[{signal_id!r}][{lang!r}] missing {field!r}"
                    )

    def test_catalog_has_german_and_english(self) -> None:
        from drift.lang._catalog import PLAIN_CATALOG

        for signal_id, templates in PLAIN_CATALOG.items():
            assert "de" in templates, f"Missing German template for {signal_id}"
            assert "en" in templates, f"Missing English template for {signal_id}"


# ---------------------------------------------------------------------------
# translate_finding()
# ---------------------------------------------------------------------------


class TestTranslateFinding:
    """translate_finding() produces human-readable messages."""

    @pytest.fixture()
    def sample_finding(self) -> Finding:
        return Finding(
            signal_type="guard_clause_deficit",
            severity=Severity.MEDIUM,
            score=0.5,
            title="Guard Clause Deficit",
            description="Function process_data lacks early-return guards.",
            file_path=Path("src/app.py"),
            start_line=42,
            symbol="process_data",
            impact=0.6,
        )

    def test_plain_german(self, sample_finding: Finding) -> None:
        from drift.lang import translate_finding

        msg = translate_finding(sample_finding, lang="de", audience="plain")
        assert isinstance(msg, str)
        assert len(msg) > 10
        # Should NOT contain the raw signal_type
        assert "guard_clause_deficit" not in msg

    def test_plain_english(self, sample_finding: Finding) -> None:
        from drift.lang import translate_finding

        msg = translate_finding(sample_finding, lang="en", audience="plain")
        assert isinstance(msg, str)
        assert len(msg) > 10

    def test_developer_mode_returns_original(self, sample_finding: Finding) -> None:
        from drift.lang import translate_finding

        msg = translate_finding(sample_finding, lang="en", audience="developer")
        # Developer mode returns the original description
        assert msg == sample_finding.description

    def test_unknown_language_falls_back_to_english(self, sample_finding: Finding) -> None:
        from drift.lang import translate_finding

        msg = translate_finding(sample_finding, lang="fr", audience="plain")
        msg_en = translate_finding(sample_finding, lang="en", audience="plain")
        assert msg == msg_en

    def test_template_variables_substituted(self, sample_finding: Finding) -> None:
        from drift.lang import translate_finding

        msg = translate_finding(sample_finding, lang="de", audience="plain")
        # The file path or symbol should appear in the message
        assert "src/app.py" in msg or "process_data" in msg

    def test_unknown_signal_returns_fallback(self) -> None:
        from drift.lang import translate_finding

        f = Finding(
            signal_type="some_unknown_plugin_signal",
            severity=Severity.LOW,
            score=0.1,
            title="Unknown signal",
            description="Something happened.",
        )
        msg = translate_finding(f, lang="de", audience="plain")
        assert isinstance(msg, str)
        assert len(msg) > 0


# ---------------------------------------------------------------------------
# Enrichment function (pipeline integration)
# ---------------------------------------------------------------------------


class TestEnrichHumanMessages:
    """enrich_human_messages() fills human_message on findings."""

    def test_enrichment_sets_human_message(self) -> None:
        from drift.lang import enrich_human_messages

        findings = [
            Finding(
                signal_type="guard_clause_deficit",
                severity=Severity.MEDIUM,
                score=0.5,
                title="Guard Clause Deficit",
                description="Missing guard clause.",
                file_path=Path("app.py"),
                symbol="do_thing",
            ),
        ]
        enriched = enrich_human_messages(findings, lang="de", audience="plain")
        assert enriched[0].human_message is not None
        assert len(enriched[0].human_message) > 10

    def test_enrichment_developer_mode_leaves_none(self) -> None:
        from drift.lang import enrich_human_messages

        findings = [
            Finding(
                signal_type="guard_clause_deficit",
                severity=Severity.MEDIUM,
                score=0.5,
                title="Guard Clause Deficit",
                description="Missing guard clause.",
            ),
        ]
        enriched = enrich_human_messages(findings, lang="en", audience="developer")
        assert enriched[0].human_message is None

    def test_enrichment_does_not_mutate_original(self) -> None:
        from drift.lang import enrich_human_messages

        f = Finding(
            signal_type="pattern_fragmentation",
            severity=Severity.HIGH,
            score=0.7,
            title="PFS",
            description="Fragments found.",
        )
        enriched = enrich_human_messages([f], lang="de", audience="plain")
        # Original should be untouched (we return new list)
        assert f.human_message is None
        assert enriched[0].human_message is not None
