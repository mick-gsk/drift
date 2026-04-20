"""Tests for drift.intent._models, _storage, and capture.py (Intent Guardian)."""
from __future__ import annotations

from pathlib import Path

from drift.intent import CapturedIntent, FeedbackActionItem, FeedbackResult, VerifyResult
from drift.intent.capture import (
    _detect_output_type,
    _extract_features,
    _is_vague,
    extract_intent,
)

# ── Model tests ───────────────────────────────────────────────────────────────


def test_captured_intent_creation() -> None:
    intent = CapturedIntent(
        intent_id="test-001",
        raw="Baue eine Finanzverwaltungs-App",
        summary="Baue eine Finanzverwaltungs-App",
        required_features=["Finanzverwaltung"],
        output_type="web_app",
        confidence=0.8,
        clarification_needed=False,
    )
    assert intent.intent_id == "test-001"
    assert intent.output_type == "web_app"
    assert intent.clarification_needed is False


def test_verify_result_creation() -> None:
    verify = VerifyResult(
        status="incomplete",
        confidence=0.6,
        missing=["Login"],
        agent_feedback="Bitte implementiere: Login",
        iteration=1,
    )
    assert verify.status == "incomplete"
    assert verify.confidence == 0.6


def test_feedback_result_creation() -> None:
    feedback = FeedbackResult(
        actions=[FeedbackActionItem(priority=1, action="add_feature", description="Login")],
        estimated_complexity="low",
    )
    assert feedback.estimated_complexity == "low"
    assert len(feedback.actions) == 1


def test_captured_intent_extra_fields_ignored() -> None:
    """extra='ignore' allows forward-compat payloads."""
    intent = CapturedIntent(
        intent_id="x",
        raw="x",
        summary="x",
        required_features=[],
        output_type="unknown",
        confidence=0.5,
        clarification_needed=False,
        unknown_future_field="ignored",  # type: ignore[call-arg]
    )
    assert intent.intent_id == "x"


# ── Storage tests ─────────────────────────────────────────────────────────────


def test_intent_store_path(tmp_path: Path) -> None:
    from drift.intent._storage import intent_store_path

    p = intent_store_path("abc-123", repo_root=tmp_path)
    assert "intents" in str(p)
    assert "abc-123.json" in str(p)


def test_save_and_load_intent(tmp_path: Path) -> None:
    from drift.intent._storage import load_intent, save_intent

    intent = CapturedIntent(
        intent_id="save-test",
        raw="Teste Speicherung",
        summary="Teste Speicherung",
        required_features=["Speicherung"],
        output_type="unknown",
        confidence=0.7,
        clarification_needed=False,
    )
    save_intent(intent, repo_root=tmp_path)
    loaded = load_intent("save-test", repo_root=tmp_path)
    assert loaded is not None
    assert loaded.intent_id == "save-test"
    assert loaded.required_features == ["Speicherung"]


def test_load_nonexistent_intent(tmp_path: Path) -> None:
    from drift.intent._storage import load_intent

    assert load_intent("does-not-exist", repo_root=tmp_path) is None


# ── Capture logic tests ───────────────────────────────────────────────────────


def test_detect_output_type_web_app() -> None:
    assert _detect_output_type("Ich möchte eine Website mit Dashboard") == "web_app"


def test_detect_output_type_unknown() -> None:
    assert _detect_output_type("hello") == "unknown"


def test_extract_features_returns_list() -> None:
    features = _extract_features("Finanzverwaltung mit Export-Funktion und Dashboard")
    assert isinstance(features, list)
    assert len(features) >= 1


def test_is_vague_short_input() -> None:
    assert _is_vague("App bauen") is True
    assert _is_vague("Ich möchte eine vollständige Finanzverwaltungs-App mit Dashboard") is False


def test_extract_intent_full() -> None:
    intent = extract_intent(
        "Ich möchte eine Finanzverwaltungs-App mit Dashboard und Export-Funktion"
    )
    assert intent.intent_id.startswith("intent-")
    assert intent.output_type in {"unknown", "web_app"}  # "Dashboard" may trigger web_app
    assert intent.clarification_needed is False
    assert len(intent.required_features) >= 1


def test_extract_intent_vague_sets_clarification() -> None:
    intent = extract_intent("App")
    assert intent.clarification_needed is True
    assert intent.clarification_question is not None
