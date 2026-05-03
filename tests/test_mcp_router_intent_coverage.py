"""Tests for mcp_router_intent.py — intent-loop router (0% coverage → 80%+).

Covers:
  - run_capture_intent: no session, with session touch
  - run_verify_intent: no session, with session touch
  - run_feedback_for_agent: no session, with session touch

Note: drift.api re-exports capture_intent/verify_intent/feedback_for_agent as
functions, shadowing the submodule names.  We must use importlib.import_module
to reach the actual submodule for monkeypatching.
"""

from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock


def _run(coro):
    return asyncio.run(coro)


def _patch_api_fn(monkeypatch, module_name: str, fn_name: str, replacement):
    """Patch a function on an actual submodule, bypassing drift.api re-export shadowing."""
    mod = importlib.import_module(module_name)
    monkeypatch.setattr(mod, fn_name, replacement)


class TestRunCaptureIntent:
    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_capture_intent

        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: None,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        captured_args: dict = {}

        def _fake_capture_intent(*, raw, path):
            captured_args["raw"] = raw
            captured_args["path"] = path
            return {"type": "ok", "intent_id": "i1"}

        _patch_api_fn(monkeypatch, "drift.api.capture_intent", "capture_intent", _fake_capture_intent)

        result = json.loads(
            _run(
                run_capture_intent(
                    raw="add logging to auth module",
                    path="/repo",
                    session_id="",
                )
            )
        )
        assert result["type"] == "ok"
        assert result["intent_id"] == "i1"
        assert captured_args["raw"] == "add logging to auth module"

    def test_with_session_touches_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_capture_intent

        session = SimpleNamespace(touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: session,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        _patch_api_fn(
            monkeypatch,
            "drift.api.capture_intent",
            "capture_intent",
            lambda **kwargs: {"type": "ok"},
        )

        _run(
            run_capture_intent(
                raw="refactor db layer",
                path=".",
                session_id="sid1",
            )
        )
        session.touch.assert_called_once()


class TestRunVerifyIntent:
    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_verify_intent

        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: None,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        captured_args: dict = {}

        def _fake_verify_intent(*, intent_id, artifact_path, path):
            captured_args.update(
                intent_id=intent_id, artifact_path=artifact_path, path=path
            )
            return {"type": "ok", "verified": True}

        _patch_api_fn(monkeypatch, "drift.api.verify_intent", "verify_intent", _fake_verify_intent)

        result = json.loads(
            _run(
                run_verify_intent(
                    intent_id="i1",
                    artifact_path="/build/output.py",
                    path="/repo",
                    session_id="",
                )
            )
        )
        assert result["verified"] is True
        assert captured_args["intent_id"] == "i1"

    def test_with_session_touches_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_verify_intent

        session = SimpleNamespace(touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: session,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        _patch_api_fn(
            monkeypatch,
            "drift.api.verify_intent",
            "verify_intent",
            lambda **kwargs: {"type": "ok"},
        )

        _run(
            run_verify_intent(
                intent_id="i2",
                artifact_path="/out.py",
                path="/repo",
                session_id="sid1",
            )
        )
        session.touch.assert_called_once()


class TestRunFeedbackForAgent:
    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_feedback_for_agent

        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: None,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        captured_args: dict = {}

        def _fake_feedback(*, intent_id, path, artifact_path):
            captured_args.update(
                intent_id=intent_id, path=path, artifact_path=artifact_path
            )
            return {"type": "ok", "actions": ["fix lint", "add tests"]}

        _patch_api_fn(monkeypatch, "drift.api.feedback_for_agent", "feedback_for_agent", _fake_feedback)

        result = json.loads(
            _run(
                run_feedback_for_agent(
                    intent_id="i3",
                    path="/repo",
                    artifact_path="/out.py",
                    session_id="",
                )
            )
        )
        assert result["type"] == "ok"
        assert "actions" in result
        assert captured_args["intent_id"] == "i3"

    def test_with_session_touches_session(self, monkeypatch) -> None:
        from drift.mcp_router_intent import run_feedback_for_agent

        session = SimpleNamespace(touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_intent._resolve_session",
            lambda _sid: session,
        )

        async def _fake_run_sync_in_thread(fn, *, abandon_on_cancel=False):
            return fn()

        monkeypatch.setattr(
            "drift.mcp_router_intent._run_sync_in_thread",
            _fake_run_sync_in_thread,
        )
        monkeypatch.setattr(
            "drift.mcp_router_intent._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        _patch_api_fn(
            monkeypatch,
            "drift.api.feedback_for_agent",
            "feedback_for_agent",
            lambda **kwargs: {"type": "ok"},
        )

        _run(
            run_feedback_for_agent(
                intent_id="i4",
                path=".",
                artifact_path="/out.py",
                session_id="sid1",
            )
        )
        session.touch.assert_called_once()
