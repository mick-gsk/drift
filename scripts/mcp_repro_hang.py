"""Minimal MCP client repro: demonstrates event-loop blocking by sync tools.

Usage:
    python scripts/mcp_repro_hang.py

What this does:
    1. Starts the drift MCP server as a subprocess on stdio
    2. Sends initialize, then tools/list, then tools/call for drift_validate
    3. Sends a second tools/call (drift_explain) immediately — this one will
       hang or time out because the event loop is blocked by the first call.

Expected behaviour BEFORE fix:
    - First tool call succeeds but blocks the event loop
    - Second tool call times out (the server can't read it from stdin)

Expected behaviour AFTER fix:
    - Both calls complete within their timeouts
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from pathlib import Path

REPO = str(Path(__file__).resolve().parent.parent)
PYTHON = str(Path(REPO) / ".venv" / "Scripts" / "python.exe")

# --- JSON-RPC helpers ---


def jsonrpc(method: str, params: dict | None = None, id: int | None = None) -> str:
    msg: dict = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if id is not None:
        msg["id"] = id
    return json.dumps(msg) + "\n"


def _reader_thread(proc: subprocess.Popen, q: queue.Queue) -> None:
    """Background thread that reads JSON lines from server stdout."""
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            line = line.strip()
            if line:
                try:
                    q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except (OSError, ValueError):
        pass


def read_response(q: queue.Queue, timeout: float = 30.0) -> dict | None:
    """Read one JSON-RPC response from the queue with timeout."""
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        return None


def main() -> None:
    print(f"[repro] Starting MCP server: {PYTHON} -m drift mcp --serve")
    proc = subprocess.Popen(
        [PYTHON, "-m", "drift", "mcp", "--serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=REPO,
    )

    # Start background reader thread
    q: queue.Queue[dict] = queue.Queue()
    reader = threading.Thread(
        target=_reader_thread, args=(proc, q), daemon=True,
    )
    reader.start()

    try:
        # 1. initialize
        print("[repro] Sending initialize...")
        proc.stdin.write(jsonrpc("initialize", {  # type: ignore[union-attr]
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "repro", "version": "0.1"},
        }, id=1))
        proc.stdin.flush()  # type: ignore[union-attr]

        resp = read_response(q, timeout=10)
        if not resp:
            print("[repro] FAIL: No initialize response")
            return
        server = resp.get("result", {}).get("serverInfo")
        print(f"[repro] initialize OK: serverInfo={server}")

        # 2. notifications/initialized
        proc.stdin.write(  # type: ignore[union-attr]
            jsonrpc("notifications/initialized"),
        )
        proc.stdin.flush()  # type: ignore[union-attr]
        time.sleep(0.2)

        # 3. tools/list
        print("[repro] Sending tools/list...")
        proc.stdin.write(  # type: ignore[union-attr]
            jsonrpc("tools/list", {}, id=2),
        )
        proc.stdin.flush()  # type: ignore[union-attr]

        resp = read_response(q, timeout=10)
        if not resp:
            print("[repro] FAIL: No tools/list response")
            return
        tools = [
            t["name"]
            for t in resp.get("result", {}).get("tools", [])
        ]
        print(f"[repro] tools/list OK: {tools}")

        # 4. tools/call drift_validate — blocks event loop (pre-fix)
        print("[repro] Sending tools/call drift_validate...")
        t0 = time.monotonic()
        proc.stdin.write(jsonrpc("tools/call", {  # type: ignore[union-attr]
            "name": "drift_validate",
            "arguments": {"path": REPO},
        }, id=3))
        proc.stdin.flush()  # type: ignore[union-attr]

        # 5. Immediately send drift_explain — tests concurrency
        print("[repro] Sending tools/call drift_explain (concurrent)...")
        proc.stdin.write(jsonrpc("tools/call", {  # type: ignore[union-attr]
            "name": "drift_explain",
            "arguments": {"topic": "PFS"},
        }, id=4))
        proc.stdin.flush()  # type: ignore[union-attr]

        # 6. Read responses
        resp3 = read_response(q, timeout=60)
        t1 = time.monotonic()
        if resp3:
            print(
                f"[repro] Response in {t1 - t0:.1f}s"
                f" (id={resp3.get('id')})",
            )
        else:
            print(
                f"[repro] FAIL: timed out after {t1 - t0:.1f}s",
            )

        resp4 = read_response(q, timeout=30)
        t2 = time.monotonic()
        if resp4:
            print(
                f"[repro] Response in {t2 - t0:.1f}s"
                f" (id={resp4.get('id')})",
            )
        else:
            print(
                "[repro] FAIL: drift_explain timed out after"
                f" {t2 - t0:.1f}s — EVENT LOOP BLOCKED",
            )

    finally:
        proc.terminate()
        proc.wait(timeout=5)
        stderr = proc.stderr.read() if proc.stderr else ""  # type: ignore[union-attr]
        if stderr:
            print(f"[repro] Server stderr: {stderr[:500]}")


if __name__ == "__main__":
    main()
