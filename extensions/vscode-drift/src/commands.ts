/**
 * Command handlers — registered in extension.ts and delegating to
 * DriftMcpClient, DriftStatusBar, and DriftDiagnostics.
 *
 * Registered commands:
 *   drift.analyzeWorkspace   — full drift_scan of workspace root
 *   drift.nudgeCurrentFile   — drift_nudge for the active (or supplied) file
 *   drift.openFindings       — quick-pick list of all current findings
 *   drift.clearDiagnostics   — wipe the drift diagnostic collection
 *
 * Decision: ADR-101
 */

import * as vscode from "vscode";
import type { DriftMcpClient } from "./mcpClient.js";
import type { DriftStatusBar } from "./statusBar.js";
import type { DriftDiagnostics } from "./diagnostics.js";

export function registerCommands(
  context: vscode.ExtensionContext,
  mcpClient: DriftMcpClient,
  statusBar: DriftStatusBar,
  diagnostics: DriftDiagnostics,
  outputChannel: vscode.OutputChannel
): void {
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "drift.analyzeWorkspace",
      () => analyzeWorkspace(mcpClient, statusBar, diagnostics, outputChannel)
    ),
    vscode.commands.registerCommand(
      "drift.nudgeCurrentFile",
      (filePath?: string) =>
        nudgeCurrentFile(
          mcpClient,
          statusBar,
          outputChannel,
          filePath
        )
    ),
    vscode.commands.registerCommand(
      "drift.openFindings",
      () => openFindings(diagnostics)
    ),
    vscode.commands.registerCommand("drift.clearDiagnostics", () => {
      diagnostics.clear();
      statusBar.showIdle();
    })
  );
}

// ---------------------------------------------------------------------------
// analyze workspace
// ---------------------------------------------------------------------------

async function analyzeWorkspace(
  mcpClient: DriftMcpClient,
  statusBar: DriftStatusBar,
  diagnostics: DriftDiagnostics,
  outputChannel: vscode.OutputChannel
): Promise<void> {
  const workspacePath = getWorkspacePath();
  if (!workspacePath) {
    vscode.window.showWarningMessage(
      "Drift: No workspace folder open. Please open a folder to analyze."
    );
    return;
  }

  statusBar.showAnalyzing();

  // Connect lazily on first use.
  if (!mcpClient.isConnected) {
    try {
      await mcpClient.connect();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      statusBar.showError("server unavailable");
      vscode.window
        .showErrorMessage(`Drift: ${msg}`, "Open Settings")
        .then((choice) => {
          if (choice === "Open Settings") {
            vscode.commands.executeCommand(
              "workbench.action.openSettings",
              "drift.pythonPath"
            );
          }
        });
      return;
    }
  }

  const maxFindings = vscode.workspace
    .getConfiguration("drift")
    .get<number>("maxFindings", 50);

  try {
    outputChannel.appendLine(
      `[drift] Running drift_scan on ${workspacePath} (max ${maxFindings} findings)`
    );
    const result = await mcpClient.scan(workspacePath, maxFindings);

    if (result.error) {
      statusBar.showError(result.error_code ?? "scan-error");
      vscode.window.showErrorMessage(`Drift scan error: ${result.error}`);
      return;
    }

    diagnostics.update(result.findings ?? []);
    const score = result.drift_score ?? result.composite_score ?? result.score;
    statusBar.updateFromScan(result.findings ?? [], score);

    const total = result.findings?.length ?? 0;
    outputChannel.appendLine(
      `[drift] Scan complete: ${total} finding(s), score=${score?.toFixed(2) ?? "n/a"}`
    );

    if (total === 0) {
      vscode.window.showInformationMessage(
        "Drift: No findings — workspace looks clean!"
      );
    } else {
      vscode.window
        .showInformationMessage(
          `Drift: ${total} finding(s) found. Click to browse.`,
          "Show Findings"
        )
        .then((choice) => {
          if (choice === "Show Findings") {
            vscode.commands.executeCommand("drift.openFindings");
          }
        });
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    outputChannel.appendLine(`[drift] Scan failed: ${msg}`);
    statusBar.showError("scan failed");
    vscode.window.showErrorMessage(`Drift scan failed: ${msg}`);
  }
}

// ---------------------------------------------------------------------------
// nudge current file
// ---------------------------------------------------------------------------

async function nudgeCurrentFile(
  mcpClient: DriftMcpClient,
  statusBar: DriftStatusBar,
  outputChannel: vscode.OutputChannel,
  filePath?: string
): Promise<void> {
  const workspacePath = getWorkspacePath();
  if (!workspacePath) {
    return;
  }

  const targetFile =
    filePath ?? vscode.window.activeTextEditor?.document.uri.fsPath;
  if (!targetFile) {
    vscode.window.showWarningMessage(
      "Drift: No active file to nudge. Open a file first."
    );
    return;
  }

  if (!mcpClient.isConnected) {
    // Silent: nudge is fast-path, not worth interrupting the user if not running.
    outputChannel.appendLine(
      "[drift] Nudge skipped: MCP server not connected. Run 'Drift: Analyze Workspace' first."
    );
    return;
  }

  statusBar.showNudging();

  try {
    outputChannel.appendLine(`[drift] Running drift_nudge on ${targetFile}`);
    const result = await mcpClient.nudge(workspacePath, targetFile);

    if (result.error) {
      outputChannel.appendLine(`[drift] Nudge error: ${result.error}`);
      statusBar.showIdle();
      return;
    }

    statusBar.updateFromNudge(result.direction, result.score);

    const icon =
      result.direction === "improving"
        ? "↑"
        : result.direction === "degrading"
          ? "↓"
          : "→";

    const revertHint =
      result.revert_recommended === true
        ? " — consider reverting this edit."
        : "";

    vscode.window.showInformationMessage(
      `Drift nudge: ${icon} ${result.direction}${revertHint}`
    );

    outputChannel.appendLine(
      `[drift] Nudge: direction=${result.direction}, safe_to_commit=${result.safe_to_commit}`
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    outputChannel.appendLine(`[drift] Nudge failed: ${msg}`);
    statusBar.showIdle();
  }
}

// ---------------------------------------------------------------------------
// open findings
// ---------------------------------------------------------------------------

async function openFindings(diagnostics: DriftDiagnostics): Promise<void> {
  const all = diagnostics.allFindings();
  if (all.length === 0) {
    vscode.window.showInformationMessage(
      "Drift: No findings. Run 'Drift: Analyze Workspace' first."
    );
    return;
  }

  const items: vscode.QuickPickItem[] = all.map(({ uri, diagnostic }) => {
    const label = diagnostic.code
      ? `$(${severityIcon(diagnostic.severity)}) [${diagnostic.code}] ${shortPath(uri)}`
      : `$(${severityIcon(diagnostic.severity)}) ${shortPath(uri)}`;
    const detail = `Line ${diagnostic.range.start.line + 1}: ${diagnostic.message}`;
    return { label, detail, description: uri.fsPath };
  });

  const picked = await vscode.window.showQuickPick(items, {
    placeHolder: `${all.length} Drift finding(s) — select to navigate`,
    matchOnDetail: true,
    matchOnDescription: true,
  });

  if (picked?.description) {
    const uri = vscode.Uri.file(picked.description);
    const doc = await vscode.workspace.openTextDocument(uri);
    const line = Number(
      picked.detail?.match(/^Line (\d+)/)?.[1] ?? "1"
    ) - 1;
    await vscode.window.showTextDocument(doc, {
      selection: new vscode.Range(line, 0, line, 0),
    });
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWorkspacePath(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function severityIcon(severity: vscode.DiagnosticSeverity): string {
  switch (severity) {
    case vscode.DiagnosticSeverity.Error:
      return "error";
    case vscode.DiagnosticSeverity.Warning:
      return "warning";
    case vscode.DiagnosticSeverity.Information:
      return "info";
    default:
      return "lightbulb";
  }
}

function shortPath(uri: vscode.Uri): string {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (root && uri.fsPath.startsWith(root)) {
    return uri.fsPath.slice(root.length).replace(/^[/\\]/, "");
  }
  return uri.fsPath;
}
