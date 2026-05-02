"""Tests for session_handover gate (ADR-079).

Covers:
  - Change-class classification from touched-file paths.
  - Required-artifact derivation per class.
  - L1 existence + size checks.
  - L2 shape checks (frontmatter + required sections + session-state cross-check).
  - L3 placeholder denylist.
  - ValidationResult composition and ordering.

Tests use the public API of ``drift.session_handover`` and the real ``DriftSession``
dataclass; no MCP tool is invoked here. Gate wiring is tested separately in
``test_mcp_hardening.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from drift.session import DriftSession, SessionManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_sessions() -> Any:
    SessionManager.reset_instance()
    yield
    SessionManager.reset_instance()


@pytest.fixture()
def session(tmp_path: Path) -> DriftSession:
    mgr = SessionManager.instance()
    sid = mgr.create(repo_path=str(tmp_path))
    s = mgr.get(sid)
    assert s is not None
    return s


def _good_frontmatter(session: DriftSession, change_class: str) -> str:
    return (
        "---\n"
        f'session_id: "{session.session_id}"\n'
        'started_at: "2026-04-21T09:15:30Z"\n'
        'ended_at: "2026-04-21T09:47:12Z"\n'
        "duration_seconds: 1902\n"
        "tool_calls: 42\n"
        "tasks_completed: 0\n"
        "tasks_remaining: 0\n"
        "findings_delta: 0\n"
        f'change_class: "{change_class}"\n'
        f'repo_path: "{session.repo_path}"\n'
        'git_head_at_plan: "a1b2c3d4"\n'
        'git_head_at_end: "e5f6a7b8"\n'
        "adr_refs: []\n"
        "evidence_files: []\n"
        "audit_artifacts_updated: []\n"
        "---\n"
    )


def _good_sections() -> str:
    return (
        "\n## Scope\n\n"
        "Session bearbeitete Klassifikation und Validator im neuen Modul. "
        "Nicht berührt: Signal-Heuristik, Fixtures.\n\n"
        "Berührte Dateien:\n\n"
        "```\nsrc/drift/session_handover.py\n```\n\n"
        "## Ergebnisse\n\n"
        "Neues Modul mit 3 Hauptfunktionen, 42 Tests grün, "
        "self-analysis unverändert.\n\n"
        "## Offene Enden\n\n"
        "Keine offenen Enden.\n\n"
        "## Next-Agent-Einstieg\n\n"
        "1. Startbefehl:\n\n"
        "```\ndrift_session_start(path='.', autopilot=true)\n```\n\n"
        "2. Relevante Pfade:\n\n"
        "- src/drift/session_handover.py\n\n"
        "3. Abnahmekriterium:\n\n"
        "Gate lehnt leere ADRs ab.\n\n"
        "## Evidenz\n\n"
        "- Evidence: n/a\n"
        "- ADR: n/a\n"
        "- Audit-Updates: n/a\n"
    )


def _write_session_md(
    repo: Path, session: DriftSession, *, change_class: str = "docs", body: str | None = None
) -> Path:
    path = repo / "work_artifacts" / f"session_{session.session_id[:8]}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _good_frontmatter(session, change_class) + (body or _good_sections())
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassifyTouched:
    """classify_touched derives ChangeClass from path list alone."""

    def test_signals_path_maps_to_signal(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert classify_touched(["src/drift/signals/pfs.py"]) is ChangeClass.SIGNAL

    def test_scoring_path_maps_to_signal(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert classify_touched(["src/drift/scoring/weights.py"]) is ChangeClass.SIGNAL

    def test_ingestion_path_maps_to_architecture(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert (
            classify_touched(["src/drift/ingestion/file_discovery.py"])
            is ChangeClass.ARCHITECTURE
        )

    def test_mcp_server_maps_to_architecture(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert (
            classify_touched(["src/drift/mcp_server.py"]) is ChangeClass.ARCHITECTURE
        )

    def test_other_src_drift_maps_to_fix(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert classify_touched(["src/drift/utils.py"]) is ChangeClass.FIX

    def test_docs_only_maps_to_docs(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert (
            classify_touched(["docs/STUDY.md", ".github/prompts/foo.prompt.md"])
            is ChangeClass.DOCS
        )

    def test_lockfile_only_maps_to_chore(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert classify_touched(["uv.lock", "pyproject.toml"]) is ChangeClass.CHORE

    def test_empty_maps_to_chore(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        assert classify_touched([]) is ChangeClass.CHORE

    def test_highest_class_wins(self) -> None:
        from drift.session_handover import ChangeClass, classify_touched

        paths = [
            "docs/STUDY.md",
            "src/drift/signals/mds.py",
            "uv.lock",
        ]
        assert classify_touched(paths) is ChangeClass.SIGNAL


# ---------------------------------------------------------------------------
# Required artifacts
# ---------------------------------------------------------------------------


class TestRequiredArtifacts:
    def test_signal_requires_evidence_adr_session(self, session: DriftSession) -> None:
        from drift.session_handover import ChangeClass, required_artifacts

        req = required_artifacts(ChangeClass.SIGNAL, session)
        kinds = {r.kind for r in req}
        assert kinds == {"evidence", "adr", "session_md"}

    def test_architecture_requires_evidence_adr_session(
        self, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, required_artifacts

        req = required_artifacts(ChangeClass.ARCHITECTURE, session)
        kinds = {r.kind for r in req}
        assert kinds == {"evidence", "adr", "session_md"}

    def test_fix_requires_only_session_md(self, session: DriftSession) -> None:
        from drift.session_handover import ChangeClass, required_artifacts

        req = required_artifacts(ChangeClass.FIX, session)
        kinds = {r.kind for r in req}
        assert kinds == {"session_md"}

    def test_docs_requires_only_session_md(self, session: DriftSession) -> None:
        from drift.session_handover import ChangeClass, required_artifacts

        req = required_artifacts(ChangeClass.DOCS, session)
        kinds = {r.kind for r in req}
        assert kinds == {"session_md"}

    def test_session_md_path_uses_first_eight_chars(
        self, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, required_artifacts

        req = required_artifacts(ChangeClass.DOCS, session)
        session_md = next(r for r in req if r.kind == "session_md")
        assert session_md.path.endswith(f"session_{session.session_id[:8]}.md")
        assert "work_artifacts" in session_md.path


# ---------------------------------------------------------------------------
# L1 existence
# ---------------------------------------------------------------------------


class TestL1Existence:
    def test_missing_session_md_blocks(self, tmp_path: Path, session: DriftSession) -> None:
        from drift.session_handover import ChangeClass, validate

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        missing_kinds = {m.kind for m in result.missing}
        assert "session_md" in missing_kinds

    def test_too_small_session_md_blocks(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        tiny = tmp_path / "work_artifacts" / f"session_{session.session_id[:8]}.md"
        tiny.parent.mkdir(parents=True, exist_ok=True)
        tiny.write_text("tiny", encoding="utf-8")

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        assert any(
            err.field == "file_size" for err in result.shape_errors
        ) or result.missing

    def test_valid_session_md_passes_l1(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        _write_session_md(tmp_path, session, change_class="docs")
        result = validate(session, change_class=ChangeClass.DOCS)
        assert not result.missing


# ---------------------------------------------------------------------------
# L2 shape
# ---------------------------------------------------------------------------


class TestL2Shape:
    def test_session_id_mismatch_blocks(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        fm = _good_frontmatter(session, "docs").replace(
            session.session_id, "00000000-0000-0000-0000-000000000000"
        )
        path = tmp_path / "work_artifacts" / f"session_{session.session_id[:8]}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(fm + _good_sections(), encoding="utf-8")

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        assert any(err.field == "session_id" for err in result.shape_errors)

    def test_missing_section_blocks(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        body = (
            "\n## Scope\n\nText.\n\n"
            "## Ergebnisse\n\nText.\n\n"
            # Offene Enden missing
            "## Next-Agent-Einstieg\n\nText.\n\n"
            "## Evidenz\n\nText.\n"
        )
        _write_session_md(tmp_path, session, change_class="docs", body=body)

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        assert any(
            err.field == "section" and "Offene Enden" in err.expected
            for err in result.shape_errors
        )

    def test_signal_class_requires_nonempty_audit_artifacts(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        # Provide all three artifacts but evidence has empty audit_artifacts_updated.
        _write_session_md(tmp_path, session, change_class="signal")
        # Fake ADR + evidence to pass existence; shape check targets evidence.
        adr_path = tmp_path / "decisions" / "ADR-999-dummy.md"
        adr_path.parent.mkdir(parents=True, exist_ok=True)
        adr_path.write_text(
            "---\nid: ADR-999\nstatus: proposed\ndate: 2026-04-21\n---\n\n"
            "# ADR-999: Dummy\n\n## Kontext\n\n"
            + ("Signal-Heuristik verändert sich und braucht Vergleichsgrundlage. " * 4)
            + "\n\nAlternative A: Nichts tun. Alternative B: Auto-Calibration einführen.\n\n"
            "## Entscheidung\n\nWir tun B.\n\n## Begründung\n\nWeil A nicht wirkt.\n\n"
            "## Konsequenzen\n\nMehr Tests nötig.\n\n## Validierung\n\nPytest grün.\n",
            encoding="utf-8",
        )
        evidence_path = tmp_path / "benchmark_results" / "v9.9.9_dummy_feature_evidence.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            '{"version": "9.9.9", "feature": "dummy", "description": "x",'
            ' "tests": {"total_passing": 1}, "audit_artifacts_updated": []}',
            encoding="utf-8",
        )

        # Override required paths so the validator finds our files.
        override = {
            "evidence": str(evidence_path),
            "adr": str(adr_path),
            "session_md": str(tmp_path / "work_artifacts"
                              / f"session_{session.session_id[:8]}.md"),
        }
        result = validate(
            session,
            change_class=ChangeClass.SIGNAL,
            path_overrides=override,
        )
        assert result.ok is False
        assert any(
            err.field == "audit_artifacts_updated" for err in result.shape_errors
        ), f"got {result.shape_errors}"


# ---------------------------------------------------------------------------
# L3 placeholder denylist
# ---------------------------------------------------------------------------


class TestL3Placeholders:
    def test_todo_in_offene_enden_blocks(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        body = (
            "\n## Scope\n\nReal stuff happened here for the docs update.\n\n"
            "## Ergebnisse\n\nUpdated 2 files.\n\n"
            "## Offene Enden\n\n- TODO: fill this out later\n\n"
            "## Next-Agent-Einstieg\n\nStart with drift_session_start.\n\n"
            "## Evidenz\n\n- Evidence: n/a\n"
        )
        _write_session_md(tmp_path, session, change_class="docs", body=body)

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        assert any(
            flag.pattern.upper() == "TODO" for flag in result.placeholder_flags
        )

    def test_lorem_ipsum_blocks(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        body = (
            "\n## Scope\n\nLorem ipsum dolor sit amet, consectetur adipiscing.\n\n"
            "## Ergebnisse\n\nDone.\n\n"
            "## Offene Enden\n\nKeine offenen Enden.\n\n"
            "## Next-Agent-Einstieg\n\ndrift_session_start\n\n"
            "## Evidenz\n\nn/a\n"
        )
        _write_session_md(tmp_path, session, change_class="docs", body=body)

        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is False
        assert any(
            "LOREM" in flag.pattern.upper() or "IPSUM" in flag.pattern.upper()
            for flag in result.placeholder_flags
        )

    def test_clean_docs_session_passes_all_layers(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        _write_session_md(tmp_path, session, change_class="docs")
        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.ok is True, (
            f"missing={result.missing} shape={result.shape_errors} "
            f"placeholders={result.placeholder_flags}"
        )


# ---------------------------------------------------------------------------
# ValidationResult aggregation
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_to_dict_contains_gate_code_when_blocked(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        result = validate(session, change_class=ChangeClass.DOCS)
        payload = result.to_dict()
        assert payload["change_class"] == "docs"
        assert payload["ok"] is False
        assert "missing_artifacts" in payload
        assert "shape_errors" in payload
        assert "placeholder_flags" in payload

    def test_semantic_ok_absent_without_llm_review(
        self, tmp_path: Path, session: DriftSession
    ) -> None:
        from drift.session_handover import ChangeClass, validate

        _write_session_md(tmp_path, session, change_class="docs")
        result = validate(session, change_class=ChangeClass.DOCS)
        assert result.semantic_ok is None
        assert "semantic_ok" not in result.to_dict()
