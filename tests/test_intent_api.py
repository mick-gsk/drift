"""Integration tests for the 3 new MCP tools (Intent Guardian)."""
from __future__ import annotations

from pathlib import Path

# ── capture_intent ────────────────────────────────────────────────────────────


def test_capture_intent_returns_intent_id(tmp_path: Path) -> None:
    from drift.api.capture_intent import capture_intent

    result = capture_intent(
        raw="Ich möchte eine Finanzverwaltungs-App mit Dashboard",
        path=str(tmp_path),
    )
    assert "intent_id" in result
    assert result["intent_id"].startswith("intent-")
    assert "next_tool_call" in result
    assert "agent_instruction" in result


def test_capture_intent_persists_to_disk(tmp_path: Path) -> None:
    from drift.api.capture_intent import capture_intent

    result = capture_intent(
        raw="Ich möchte eine Finanzverwaltungs-App mit Dashboard",
        path=str(tmp_path),
    )
    intent_file = tmp_path / ".drift" / "intents" / f"{result['intent_id']}.json"
    assert intent_file.exists()


def test_capture_intent_vague_sets_clarification(tmp_path: Path) -> None:
    from drift.api.capture_intent import capture_intent

    result = capture_intent(raw="App", path=str(tmp_path))
    assert result.get("clarification_needed") is True


# ── verify_intent ─────────────────────────────────────────────────────────────


def test_verify_intent_fulfilled(tmp_path: Path) -> None:
    from drift.api.capture_intent import capture_intent
    from drift.api.verify_intent import verify_intent

    cap = capture_intent(
        raw="Ich möchte eine Finanzverwaltungs-App mit Dashboard",
        path=str(tmp_path),
    )
    intent_id = cap["intent_id"]
    artifact = tmp_path / "build"
    artifact.mkdir()
    (artifact / "index.html").write_text(
        "<html><body>Finanzverwaltung Dashboard</body></html>", encoding="utf-8"
    )
    result = verify_intent(
        intent_id=intent_id,
        artifact_path=str(artifact),
        path=str(tmp_path),
    )
    assert result["status"] in {"fulfilled", "incomplete"}
    assert "confidence" in result


def test_verify_intent_missing_intent_returns_error(tmp_path: Path) -> None:
    from drift.api.verify_intent import verify_intent

    result = verify_intent(
        intent_id="does-not-exist",
        artifact_path=str(tmp_path),
        path=str(tmp_path),
    )
    assert "error" in result


# ── feedback_for_agent ────────────────────────────────────────────────────────


def test_feedback_for_agent_returns_actions(tmp_path: Path) -> None:
    from drift.api.capture_intent import capture_intent
    from drift.api.feedback_for_agent import feedback_for_agent

    cap = capture_intent(
        raw="Ich möchte eine Finanzverwaltungs-App mit Dashboard und Export-Funktion",
        path=str(tmp_path),
    )
    intent_id = cap["intent_id"]
    artifact = tmp_path / "build"
    artifact.mkdir()
    # Empty build — should trigger missing features
    result = feedback_for_agent(
        intent_id=intent_id,
        path=str(tmp_path),
        artifact_path=str(artifact),
    )
    assert "actions" in result
    assert "estimated_complexity" in result
    assert "next_tool_call" in result
