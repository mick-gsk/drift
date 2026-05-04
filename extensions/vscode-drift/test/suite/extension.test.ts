/**
 * Extension test suite.
 *
 * Tests:
 *   1. Activation smoke — extension activates and exposes its four commands.
 *   2. Diagnostics unit — DriftDiagnostics correctly maps Drift findings to
 *      VS Code Diagnostics with the expected severity levels (ADR-101).
 *   3. MCP client (offline) — DriftMcpClient.nudge/scan fail gracefully with
 *      an actionable error message when the server is unreachable.
 *
 * No real Drift MCP server is spawned in tests; all MCP interaction is mocked.
 */

import * as assert from "node:assert";
import * as vscode from "vscode";

// ---------------------------------------------------------------------------
// 1. Activation smoke
// ---------------------------------------------------------------------------

suite("Extension Activation", () => {
  test("all four commands are registered after activation", async () => {
    // The extension activates on `workspaceContains:drift.yaml`.
    // In the test workspace the extension may not auto-activate, so we
    // activate it explicitly via one of its commands.
    const commands = await vscode.commands.getCommands(true);
    const driftCommands = [
      "drift.analyzeWorkspace",
      "drift.nudgeCurrentFile",
      "drift.openFindings",
      "drift.clearDiagnostics",
    ];
    for (const cmd of driftCommands) {
      assert.ok(
        commands.includes(cmd),
        `Expected command '${cmd}' to be registered`
      );
    }
  });
});

// ---------------------------------------------------------------------------
// 2. Diagnostics unit
// ---------------------------------------------------------------------------

suite("DriftDiagnostics", () => {
  // Import lazily so the module resolves inside the test host.
  let DriftDiagnostics: typeof import("../../src/diagnostics.js").DriftDiagnostics;

  suiteSetup(async () => {
    const mod = await import("../../src/diagnostics.js");
    DriftDiagnostics = mod.DriftDiagnostics;
  });

  test("maps high severity to DiagnosticSeverity.Error", () => {
    const diags = new DriftDiagnostics();
    diags.update([
      {
        signal_id: "PFS",
        file: "src/foo.py",
        severity: "high",
        reason: "Too many public symbols",
        line: 10,
      },
    ]);
    const all = diags.allFindings();
    assert.strictEqual(all.length, 1);
    assert.strictEqual(
      all[0].diagnostic.severity,
      vscode.DiagnosticSeverity.Error
    );
    diags.dispose();
  });

  test("maps medium severity to DiagnosticSeverity.Warning", () => {
    const diags = new DriftDiagnostics();
    diags.update([
      {
        signal_id: "MDS",
        file: "src/bar.py",
        severity: "medium",
        reason: "Module dependency depth too high",
      },
    ]);
    const all = diags.allFindings();
    assert.strictEqual(all.length, 1);
    assert.strictEqual(
      all[0].diagnostic.severity,
      vscode.DiagnosticSeverity.Warning
    );
    diags.dispose();
  });

  test("maps low severity to DiagnosticSeverity.Information", () => {
    const diags = new DriftDiagnostics();
    diags.update([
      {
        signal_id: "EDS",
        file: "src/baz.py",
        severity: "low",
        reason: "Minor export drift",
      },
    ]);
    const all = diags.allFindings();
    assert.strictEqual(all.length, 1);
    assert.strictEqual(
      all[0].diagnostic.severity,
      vscode.DiagnosticSeverity.Information
    );
    diags.dispose();
  });

  test("clear() removes all diagnostics", () => {
    const diags = new DriftDiagnostics();
    diags.update([
      { signal_id: "PFS", file: "src/x.py", severity: "high", reason: "r" },
    ]);
    diags.clear();
    assert.strictEqual(diags.allFindings().length, 0);
    diags.dispose();
  });

  test("skips findings without a file path", () => {
    const diags = new DriftDiagnostics();
    diags.update([
      { signal_id: "PFS", file: "", severity: "high", reason: "no file" },
    ]);
    assert.strictEqual(diags.allFindings().length, 0);
    diags.dispose();
  });
});

// ---------------------------------------------------------------------------
// 3. MCP client — offline graceful failure
// ---------------------------------------------------------------------------

suite("DriftMcpClient offline", () => {
  let DriftMcpClient: typeof import("../../src/mcpClient.js").DriftMcpClient;

  suiteSetup(async () => {
    const mod = await import("../../src/mcpClient.js");
    DriftMcpClient = mod.DriftMcpClient;
  });

  test("scan() rejects with actionable message when server is not connected", async () => {
    const out = vscode.window.createOutputChannel("drift-test");
    const client = new DriftMcpClient(out);
    // Do NOT call connect() — simulate offline state.
    await assert.rejects(
      () => client.scan("/tmp/workspace", 50),
      (err: Error) => {
        assert.ok(
          err.message.includes("Drift MCP server is not running"),
          `Unexpected error message: ${err.message}`
        );
        return true;
      }
    );
    out.dispose();
  });

  test("nudge() rejects with actionable message when server is not connected", async () => {
    const out = vscode.window.createOutputChannel("drift-test-nudge");
    const client = new DriftMcpClient(out);
    await assert.rejects(
      () => client.nudge("/tmp/workspace", "/tmp/workspace/src/foo.py"),
      (err: Error) => {
        assert.ok(
          err.message.includes("Drift MCP server is not running"),
          `Unexpected error message: ${err.message}`
        );
        return true;
      }
    );
    out.dispose();
  });
});
