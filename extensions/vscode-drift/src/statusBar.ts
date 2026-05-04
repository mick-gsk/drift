/**
 * Status bar item — displays the current Drift composite score and finding
 * summary in the VS Code status bar.
 *
 * Format: $(shield) Drift · 0.71 · 3↑ (1 high, 2 med)
 *
 * Decision: ADR-101
 */

import * as vscode from "vscode";
import type { DriftFinding } from "./mcpClient.js";

export class DriftStatusBar {
  private readonly item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Left,
      10
    );
    this.item.command = "drift.openFindings";
    this.item.tooltip = "Click to show Drift findings";
    this.showIdle();
    this.item.show();
  }

  showIdle(): void {
    this.item.text = "$(shield) Drift";
    this.item.backgroundColor = undefined;
    this.item.tooltip = "Drift: no scan results yet. Run 'Drift: Analyze Workspace'.";
  }

  showAnalyzing(): void {
    this.item.text = "$(sync~spin) Drift: analyzing…";
    this.item.backgroundColor = undefined;
  }

  showNudging(): void {
    this.item.text = "$(sync~spin) Drift: nudging…";
    this.item.backgroundColor = undefined;
  }

  showError(message: string): void {
    this.item.text = "$(error) Drift: error";
    this.item.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.errorBackground"
    );
    this.item.tooltip = `Drift error: ${message}`;
  }

  updateFromScan(findings: DriftFinding[], score?: number): void {
    const highCount = findings.filter((f) => f.severity === "high").length;
    const medCount = findings.filter((f) => f.severity === "medium").length;
    const lowCount = findings.filter((f) => f.severity === "low").length;
    const total = findings.length;

    const scoreText =
      score !== undefined ? ` · ${score.toFixed(2)}` : "";
    const icon = highCount > 0 ? "$(error)" : total > 0 ? "$(warning)" : "$(check)";
    const summary =
      total === 0
        ? "no findings"
        : `${total} finding${total !== 1 ? "s" : ""}` +
          (highCount > 0 ? ` (${highCount} high)` : "") +
          (medCount > 0 && highCount === 0 ? ` (${medCount} med)` : "") +
          (lowCount > 0 && highCount === 0 && medCount === 0
            ? ` (${lowCount} low)`
            : "");

    this.item.text = `${icon} Drift${scoreText} · ${summary}`;
    this.item.backgroundColor =
      highCount > 0
        ? new vscode.ThemeColor("statusBarItem.warningBackground")
        : undefined;
    this.item.tooltip = `Drift scan complete. ${summary}. Click to browse findings.`;
  }

  updateFromNudge(direction: string, score?: number): void {
    const icon =
      direction === "improving"
        ? "$(arrow-up)"
        : direction === "degrading"
          ? "$(arrow-down)"
          : "$(dash)";
    const scoreText =
      score !== undefined ? ` · ${score.toFixed(2)}` : "";
    this.item.text = `${icon} Drift${scoreText} · ${direction}`;
    this.item.backgroundColor =
      direction === "degrading"
        ? new vscode.ThemeColor("statusBarItem.warningBackground")
        : undefined;
    this.item.tooltip = `Drift nudge: ${direction}`;
  }

  dispose(): void {
    this.item.dispose();
  }
}
