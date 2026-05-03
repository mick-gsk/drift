"""Tests for mcp_router_patch.py — patch engine router (0% coverage → 80%+).

Covers:
  - _store_patch_intent: various session states and JSON shapes
  - _store_patch_verdict: various session states and JSON shapes
  - _finalize_patch: move from active_patches to patch_history
  - run_patch_begin: async function with mocked dependencies
  - run_patch_check: session path resolution
  - run_patch_commit: session path resolution
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _store_patch_intent
# ---------------------------------------------------------------------------


class TestStorePatchIntent:
    def _get_fn(self):
        from drift.mcp_router_patch import _store_patch_intent

        return _store_patch_intent

    def test_none_session_is_noop(self) -> None:
        fn = self._get_fn()
        fn(None, "task1", json.dumps({"intent": {"x": 1}}))  # should not raise

    def test_session_without_active_patches_is_noop(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace()  # no active_patches attribute
        fn(session, "task1", json.dumps({"intent": {"x": 1}}))  # should not raise

    def test_stores_intent_in_session(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={})
        fn(session, "task1", json.dumps({"intent": {"action": "add docstring"}}))
        assert "task1" in session.active_patches
        assert session.active_patches["task1"]["intent"] == {"action": "add docstring"}

    def test_no_intent_key_does_not_store(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={})
        fn(session, "task1", json.dumps({"verdict": {"ok": True}}))
        assert "task1" not in session.active_patches

    def test_invalid_json_is_silently_ignored(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={})
        fn(session, "task1", "not-json{{{")  # should not raise
        assert session.active_patches == {}


# ---------------------------------------------------------------------------
# _store_patch_verdict
# ---------------------------------------------------------------------------


class TestStorePatchVerdict:
    def _get_fn(self):
        from drift.mcp_router_patch import _store_patch_verdict

        return _store_patch_verdict

    def test_none_session_is_noop(self) -> None:
        fn = self._get_fn()
        fn(None, "task1", json.dumps({"verdict": {"ok": True}}))

    def test_stores_verdict_when_task_exists(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={"task1": {"intent": {}}})
        fn(session, "task1", json.dumps({"verdict": {"ok": True, "score": 0.9}}))
        assert session.active_patches["task1"]["verdict"] == {"ok": True, "score": 0.9}

    def test_verdict_not_stored_if_task_absent(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={})
        fn(session, "task99", json.dumps({"verdict": {"ok": True}}))
        assert "task99" not in session.active_patches

    def test_invalid_json_silently_ignored(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={"task1": {}})
        fn(session, "task1", "garbage")

    def test_session_without_attribute_is_noop(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace()
        fn(session, "task1", json.dumps({"verdict": {}}))


# ---------------------------------------------------------------------------
# _finalize_patch
# ---------------------------------------------------------------------------


class TestFinalizePatch:
    def _get_fn(self):
        from drift.mcp_router_patch import _finalize_patch

        return _finalize_patch

    def test_none_session_is_noop(self) -> None:
        fn = self._get_fn()
        fn(None, "task1", json.dumps({"evidence": {"result": "ok"}}))

    def test_moves_to_history_and_removes_from_active(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(
            active_patches={"task1": {"intent": {}}},
            patch_history=[],
        )
        fn(session, "task1", json.dumps({"evidence": {"result": "success"}}))
        assert "task1" not in session.active_patches
        assert len(session.patch_history) == 1
        assert session.patch_history[0] == {"result": "success"}

    def test_no_evidence_key_leaves_state_unchanged(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={"task1": {}}, patch_history=[])
        fn(session, "task1", json.dumps({"other": "data"}))
        assert "task1" in session.active_patches
        assert session.patch_history == []

    def test_invalid_json_silently_ignored(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={"task1": {}}, patch_history=[])
        fn(session, "task1", "bad json")
        assert "task1" in session.active_patches

    def test_session_without_patch_history_still_removes_active(self) -> None:
        fn = self._get_fn()
        session = SimpleNamespace(active_patches={"task1": {}})
        # no patch_history attribute
        fn(session, "task1", json.dumps({"evidence": {"x": 1}}))
        assert "task1" not in session.active_patches


# ---------------------------------------------------------------------------
# run_patch_begin / run_patch_check / run_patch_commit (async, mocked)
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


class TestRunPatchBegin:
    def test_happy_path_no_session(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_begin

        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: None,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "intent": {"task_id": kwargs["task_id"]}})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        result = json.loads(
            _run(
                run_patch_begin(
                    task_id="t1",
                    declared_files="src/a.py,src/b.py",
                    expected_outcome="add docstring",
                    session_id="",
                    blast_radius="low",
                    forbidden_paths=None,
                    max_diff_lines=None,
                )
            )
        )
        assert result["type"] == "ok"
        assert result["intent"]["task_id"] == "t1"

    def test_with_session_stores_intent_and_touches(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_begin

        session = SimpleNamespace(
            active_patches={},
            touch=MagicMock(),
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: session,
        )

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            return json.dumps({"type": "ok", "intent": {"task_id": "t2"}})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        _run(
            run_patch_begin(
                task_id="t2",
                declared_files="src/a.py",
                expected_outcome="fix bug",
                session_id="sid1",
                blast_radius="medium",
                forbidden_paths=None,
                max_diff_lines=50,
            )
        )
        session.touch.assert_called_once()
        assert "t2" in session.active_patches


class TestRunPatchCheck:
    def test_path_resolved_from_session(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_check

        session = SimpleNamespace(repo_path="/repo/root", touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: session,
        )

        captured = {}

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            captured["path"] = kwargs["path"]
            return json.dumps({"type": "ok", "verdict": {"ok": True}})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._store_patch_verdict",
            lambda *_a: None,
        )

        _run(
            run_patch_check(
                task_id="t1",
                declared_files="src/a.py",
                path=".",  # should be replaced by session.repo_path
                session_id="sid1",
                forbidden_paths=None,
                max_diff_lines=None,
            )
        )
        assert captured["path"] == "/repo/root"
        session.touch.assert_called_once()

    def test_explicit_path_not_overridden_when_set(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_check

        session = SimpleNamespace(repo_path="/repo/root", touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: session,
        )

        captured = {}

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            captured["path"] = kwargs["path"]
            return json.dumps({"type": "ok"})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._store_patch_verdict",
            lambda *_a: None,
        )

        _run(
            run_patch_check(
                task_id="t1",
                declared_files="src/a.py",
                path="/explicit/path",
                session_id="sid1",
                forbidden_paths=None,
                max_diff_lines=None,
            )
        )
        assert captured["path"] == "/explicit/path"


class TestRunPatchCommit:
    def test_path_resolved_from_session(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_commit

        session = SimpleNamespace(repo_path="/repo/root", touch=MagicMock())
        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: session,
        )

        captured = {}

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            captured["path"] = kwargs["path"]
            return json.dumps({"type": "ok", "evidence": {"result": "done"}})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._finalize_patch",
            lambda *_a: None,
        )

        _run(
            run_patch_commit(
                task_id="t1",
                declared_files="src/a.py",
                expected_outcome="add docstring",
                path=".",
                session_id="sid1",
            )
        )
        assert captured["path"] == "/repo/root"
        session.touch.assert_called_once()

    def test_no_session_uses_explicit_path(self, monkeypatch) -> None:
        from drift.mcp_router_patch import run_patch_commit

        monkeypatch.setattr(
            "drift.mcp_router_patch._resolve_session",
            lambda _sid: None,
        )

        captured = {}

        async def _fake_run_api_tool(tool_name, fn, **kwargs):
            captured["path"] = kwargs["path"]
            return json.dumps({"type": "ok"})

        monkeypatch.setattr(
            "drift.mcp_router_patch._run_api_tool",
            _fake_run_api_tool,
        )
        monkeypatch.setattr(
            "drift.mcp_router_patch._enrich_response_with_session",
            lambda raw, _sess, _tool: raw,
        )

        _run(
            run_patch_commit(
                task_id="t1",
                declared_files="",
                expected_outcome="do thing",
                path="/my/repo",
                session_id="",
            )
        )
        assert captured["path"] == "/my/repo"
