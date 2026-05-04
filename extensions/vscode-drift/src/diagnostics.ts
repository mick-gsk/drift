/**
 * Diagnostics — maps Drift findings to VS Code Diagnostic objects.
 *
 * Severity mapping (Decision: ADR-101):
 *   high   → DiagnosticSeverity.Error
 *   medium → DiagnosticSeverity.Warning
 *   low    → DiagnosticSeverity.Information
 *   other  → DiagnosticSeverity.Hint
 */

import * as vscode from "vscode";
import type { DriftFinding } from "./mcpClient.js";

export class DriftDiagnostics {
  private readonly collection: vscode.DiagnosticCollection;
  private readonly source = "drift";

  constructor() {
    this.collection = vscode.languages.createDiagnosticCollection(this.source);
  }

  /**
   * Replace the entire diagnostic set with the supplied findings.
   *
   * Files not present in `findings` keep any existing diagnostics unless
   * `clearOthers` is true (default: true).
   */
  update(findings: DriftFinding[], clearOthers = true): void {
    if (clearOthers) {
      this.collection.clear();
    }

    const byFile = new Map<string, DriftFinding[]>();
    for (const finding of findings) {
      if (!finding.file) {
        continue;
      }
      const list = byFile.get(finding.file) ?? [];
      list.push(finding);
      byFile.set(finding.file, list);
    }

    for (const [filePath, filefindings] of byFile) {
      // Build a URI from the finding's file path. Drift returns paths
      // relative to the repo root; try to resolve them against the first
      // workspace folder.
      const uri = this.resolveUri(filePath);
      const diagnostics = filefindings.map((f) =>
        this.buildDiagnostic(f)
      );
      this.collection.set(uri, diagnostics);
    }
  }

  clear(): void {
    this.collection.clear();
  }

  /** Return all currently tracked findings as a flat array for display. */
  allFindings(): Array<{ uri: vscode.Uri; diagnostic: vscode.Diagnostic }> {
    const result: Array<{ uri: vscode.Uri; diagnostic: vscode.Diagnostic }> =
      [];
    this.collection.forEach((uri, diagnostics) => {
      for (const d of diagnostics) {
        result.push({ uri, diagnostic: d });
      }
    });
    return result;
  }

  dispose(): void {
    this.collection.dispose();
  }

  // ---------------------------------------------------------------------------
  // Internals
  // ---------------------------------------------------------------------------

  private buildDiagnostic(finding: DriftFinding): vscode.Diagnostic {
    const severity = this.mapSeverity(finding.severity);
    // Drift findings may carry a line number (1-based); fall back to line 0.
    const line = Math.max(0, (finding.line ?? 1) - 1);
    const range = new vscode.Range(line, 0, line, Number.MAX_SAFE_INTEGER);

    const message = (() => {
      const body = finding.title ?? finding.reason ?? finding.signal_id;
      const action = finding.next_step ?? finding.next_action;
      return action ? `${body} — ${action}` : body;
    })();

    const diag = new vscode.Diagnostic(range, message, severity);
    diag.source = this.source;
    diag.code = finding.signal_id;
    return diag;
  }

  private mapSeverity(severity: string): vscode.DiagnosticSeverity {
    switch (severity) {
      case "high":
        return vscode.DiagnosticSeverity.Error;
      case "medium":
        return vscode.DiagnosticSeverity.Warning;
      case "low":
        return vscode.DiagnosticSeverity.Information;
      default:
        return vscode.DiagnosticSeverity.Hint;
    }
  }

  private resolveUri(filePath: string): vscode.Uri {
    // Absolute paths are used as-is.
    if (filePath.startsWith("/") || /^[A-Za-z]:[/\\]/.test(filePath)) {
      return vscode.Uri.file(filePath);
    }
    // Relative paths are resolved against the first workspace folder.
    const root = vscode.workspace.workspaceFolders?.[0]?.uri;
    if (root) {
      return vscode.Uri.joinPath(root, filePath);
    }
    return vscode.Uri.file(filePath);
  }
}
