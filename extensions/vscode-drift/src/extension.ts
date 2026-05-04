/**
 * Extension entry point — activate / deactivate lifecycle.
 *
 * Responsibilities:
 *   - Create shared services (MCP client, status bar, diagnostics).
 *   - Register all commands.
 *   - Wire on-save nudge if configured.
 *   - Tear down all resources on deactivation.
 *
 * Decision: ADR-101
 */

import * as vscode from "vscode";
import { DriftMcpClient } from "./mcpClient.js";
import { DriftStatusBar } from "./statusBar.js";
import { DriftDiagnostics } from "./diagnostics.js";
import { registerCommands } from "./commands.js";

let outputChannel: vscode.OutputChannel | undefined;
let mcpClient: DriftMcpClient | undefined;
let statusBar: DriftStatusBar | undefined;
let diagnostics: DriftDiagnostics | undefined;

export function activate(context: vscode.ExtensionContext): void {
  outputChannel = vscode.window.createOutputChannel("Drift");
  mcpClient = new DriftMcpClient(outputChannel);
  statusBar = new DriftStatusBar();
  diagnostics = new DriftDiagnostics();

  // Register all commands and wire them to the shared services.
  registerCommands(context, mcpClient, statusBar, diagnostics, outputChannel);

  // Optionally run nudge on save.
  const onSaveDisposable = vscode.workspace.onDidSaveTextDocument(
    async (doc) => {
      const analyzeOnSave = vscode.workspace
        .getConfiguration("drift")
        .get<boolean>("analyzeOnSave", false);
      if (!analyzeOnSave || !mcpClient?.isConnected) {
        return;
      }
      await vscode.commands.executeCommand(
        "drift.nudgeCurrentFile",
        doc.uri.fsPath
      );
    }
  );
  context.subscriptions.push(onSaveDisposable);

  outputChannel.appendLine("[drift] Extension activated.");
}

export function deactivate(): Promise<void> | void {
  outputChannel?.appendLine("[drift] Deactivating extension.");
  statusBar?.dispose();
  diagnostics?.dispose();
  return mcpClient?.disconnect();
}
