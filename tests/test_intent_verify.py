from __future__ import annotations

from pathlib import Path

from drift.intent._models import CapturedIntent
from drift.intent.verify import _scan_artifact_content, verify_artifact


def _make_intent(features: list[str]) -> CapturedIntent:
    return CapturedIntent(
        intent_id="v-test-001",
        raw="Test",
        summary="Test",
        required_features=features,
        output_type="web_app",
        confidence=0.8,
        clarification_needed=False,
    )


def test_verify_fulfilled_when_all_features_present(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<html><body>Finanzverwaltung Ausgaben Einnahmen Dashboard</body></html>",
        encoding="utf-8",
    )
    intent = _make_intent(["Finanzverwaltung", "Dashboard"])
    result = verify_artifact(intent=intent, artifact_path=tmp_path)
    assert result.status == "fulfilled"
    assert result.confidence >= 0.7


def test_verify_incomplete_when_features_missing(tmp_path: Path):
    (tmp_path / "index.html").write_text(
        "<html><body>Nur ein bisschen Text ohne Features</body></html>",
        encoding="utf-8",
    )
    intent = _make_intent(["Finanzverwaltung", "Export-Funktion", "Dashboard"])
    result = verify_artifact(intent=intent, artifact_path=tmp_path)
    assert result.status == "incomplete"
    assert len(result.missing) >= 1
    assert result.agent_feedback != ""


def test_verify_empty_artifact(tmp_path: Path):
    intent = _make_intent(["Finanzverwaltung"])
    result = verify_artifact(intent=intent, artifact_path=tmp_path)
    assert result.status == "incomplete"
    assert result.confidence < 0.5


def test_scan_artifact_content_reads_files(tmp_path: Path):
    (tmp_path / "app.py").write_text("def finanz(): pass\ndef budget(): pass", encoding="utf-8")
    (tmp_path / "readme.md").write_text("# Meine Finanzplaner App", encoding="utf-8")
    content = _scan_artifact_content(tmp_path)
    assert "finanz" in content.lower()


def test_verify_increments_iteration(tmp_path: Path):
    intent = _make_intent(["Finanzverwaltung"])
    result = verify_artifact(intent=intent, artifact_path=tmp_path, iteration=3)
    assert result.iteration == 3
