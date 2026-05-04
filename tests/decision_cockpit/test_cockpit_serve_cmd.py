"""Tests for `drift cockpit serve` command and _serve.py module.

Covers:
- T014 skeleton (RED phase): command starts, responds 200 on /, --help includes api-url option
- T048 full implementation tests
"""
from __future__ import annotations

import threading
import time

import pytest
from click.testing import CliRunner
from drift_cockpit._cmd import cockpit_cmd

# ---------------------------------------------------------------------------
# CLI help tests (fast, no network)
# ---------------------------------------------------------------------------


class TestServeCmdHelp:
    def test_help_includes_api_url(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cockpit_cmd, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--api-url" in result.output

    def test_help_includes_port(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cockpit_cmd, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output


# ---------------------------------------------------------------------------
# Server startup tests (requires fastapi + uvicorn)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def serve_port() -> int:
    return 19123


@pytest.fixture(scope="module")
def running_server(serve_port: int):
    """Start the FastAPI serve app on a free port; yield; shut down."""
    pytest.importorskip("fastapi")
    pytest.importorskip("uvicorn")

    import uvicorn
    from drift_cockpit._serve import create_app

    app = create_app(api_url="http://localhost:8001")
    config = uvicorn.Config(app, host="127.0.0.1", port=serve_port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for startup
    deadline = time.time() + 5
    import httpx
    while time.time() < deadline:
        try:
            httpx.get(f"http://127.0.0.1:{serve_port}/", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)

    yield serve_port
    server.should_exit = True


class TestServeStartup:
    def test_root_responds(self, running_server: int) -> None:
        import httpx
        resp = httpx.get(f"http://127.0.0.1:{running_server}/")
        # 200 (with assets) or 503 (no static assets bundled yet) — both are valid
        assert resp.status_code in (200, 503)

    def test_no_static_returns_503_with_hint(self, running_server: int) -> None:
        import httpx
        resp = httpx.get(f"http://127.0.0.1:{running_server}/")
        if resp.status_code == 503:
            body = resp.json()
            assert "hint" in body
            assert "cockpit-build" in body["hint"]
