/**
 * Drift MCP Client — thin wrapper around the official MCP SDK.
 *
 * Spawns `python -m drift mcp --serve` as a stdio child process and
 * exposes strongly-typed helpers for the two tools used by the extension:
 *   - `drift_scan`  — full workspace analysis
 *   - `drift_nudge` — fast directional feedback after a file edit
 *
 * Decision: ADR-101 (MCP-Client-Lib choice)
 */

import * as vscode from "vscode";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DriftFinding {
  /** Signal abbreviation (e.g. "PFS", "AVS"). Maps to signal_id/signal_abbrev in API. */
  signal_id: string;
  file: string;
  severity: "high" | "medium" | "low" | string;
  /** Human-readable message. API field: 'title' (concise) or 'description' (detailed). */
  title?: string;
  /** Legacy alias kept for fallback — not emitted by current API. */
  reason?: string;
  /** Next suggested action. API field: 'next_step'. */
  next_step?: string;
  /** Legacy alias. */
  next_action?: string;
  line?: number;
}

export interface DriftScanResult {
  findings: DriftFinding[];
  /** Composite drift score (0–1). API field: 'drift_score'. */
  drift_score?: number;
  /** Legacy alias — not emitted by current API but kept for fallback. */
  composite_score?: number;
  score?: number;
  finding_count?: number;
  total_findings?: number;
  error?: string;
  error_code?: string;
}

export interface DriftNudgeResult {
  direction: "improving" | "stable" | "degrading" | string;
  safe_to_commit: boolean;
  revert_recommended?: boolean;
  latency_exceeded?: boolean;
  baseline_created?: boolean;
  auto_fast_path?: boolean;
  changed_files?: string[];
  score?: number;
  error?: string;
  error_code?: string;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export class DriftMcpClient {
  private client: Client | null = null;
  private transport: StdioClientTransport | null = null;
  private readonly outputChannel: vscode.OutputChannel;

  constructor(outputChannel: vscode.OutputChannel) {
    this.outputChannel = outputChannel;
  }

  /** Resolve the Python executable to use, honouring the drift.pythonPath setting. */
  private resolvePython(): string {
    const configured = vscode.workspace
      .getConfiguration("drift")
      .get<string>("pythonPath", "");
    if (configured && configured.trim().length > 0) {
      return configured.trim();
    }
    // Fall back to workspace-local venv on each platform.
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (workspaceFolders && workspaceFolders.length > 0) {
      const root = workspaceFolders[0].uri.fsPath;
      const sep = process.platform === "win32" ? "\\" : "/";
      const candidate =
        process.platform === "win32"
          ? `${root}${sep}.venv${sep}Scripts${sep}python.exe`
          : `${root}${sep}.venv${sep}bin${sep}python`;
      return candidate;
    }
    return "python";
  }

  /** Start (or restart) the MCP server connection. */
  async connect(): Promise<void> {
    await this.disconnect();

    const python = this.resolvePython();
    this.outputChannel.appendLine(
      `[drift] Starting MCP server: ${python} -m drift mcp --serve`
    );

    this.transport = new StdioClientTransport({
      command: python,
      args: ["-m", "drift", "mcp", "--serve"],
      stderr: "pipe",
    });

    this.client = new Client(
      { name: "vscode-drift", version: "0.1.0" },
      { capabilities: {} }
    );

    try {
      await this.client.connect(this.transport);
      this.outputChannel.appendLine("[drift] MCP server connected.");
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.outputChannel.appendLine(
        `[drift] Failed to connect to MCP server: ${message}`
      );
      this.client = null;
      this.transport = null;
      throw new Error(
        `Drift MCP server could not be started.\n\nMake sure drift-analyzer is installed in the Python environment used by this workspace.\n\nDetails: ${message}`
      );
    }
  }

  /** Gracefully close the MCP connection. */
  async disconnect(): Promise<void> {
    if (this.client) {
      try {
        await this.client.close();
      } catch {
        // Ignore close errors — process may already be gone.
      }
      this.client = null;
      this.transport = null;
    }
  }

  get isConnected(): boolean {
    return this.client !== null;
  }

  // ---------------------------------------------------------------------------
  // Tools
  // ---------------------------------------------------------------------------

  /**
   * Run a full workspace scan via `drift_scan`.
   *
   * @param workspacePath  Absolute path to the repository root.
   * @param maxFindings    Upper bound on returned findings.
   */
  async scan(
    workspacePath: string,
    maxFindings: number
  ): Promise<DriftScanResult> {
    const raw = await this.callTool("drift_scan", {
      path: workspacePath,
      max_findings: maxFindings,
      response_detail: "concise",
    });
    return this.parseJson<DriftScanResult>(raw, { findings: [] });
  }

  /**
   * Run a fast nudge for a single changed file via `drift_nudge`.
   *
   * @param workspacePath  Absolute path to the repository root.
   * @param changedFile    Absolute or repo-relative path of the changed file.
   */
  async nudge(
    workspacePath: string,
    changedFile: string
  ): Promise<DriftNudgeResult> {
    const raw = await this.callTool("drift_nudge", {
      path: workspacePath,
      changed_files: changedFile,
      timeout_ms: 1000,
    });
    return this.parseJson<DriftNudgeResult>(raw, {
      direction: "stable",
      safe_to_commit: true,
    });
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  private async callTool(
    name: string,
    args: Record<string, unknown>
  ): Promise<string> {
    if (!this.client) {
      throw new Error(
        "Drift MCP server is not running. Run 'Drift: Analyze Workspace' to start it."
      );
    }
    const result = await this.client.callTool({ name, arguments: args });
    // The MCP SDK returns content as an array of ContentItem.
    const content = result.content;
    if (Array.isArray(content)) {
      for (const item of content) {
        if (
          item &&
          typeof item === "object" &&
          "type" in item &&
          item.type === "text" &&
          "text" in item
        ) {
          return String(item.text);
        }
      }
    }
    return JSON.stringify(result);
  }

  private parseJson<T>(raw: string, fallback: T): T {
    try {
      // Drift responses may contain Rich-style trailing text; extract JSON.
      const start = raw.indexOf("{");
      const end = raw.lastIndexOf("}");
      if (start >= 0 && end > start) {
        return JSON.parse(raw.slice(start, end + 1)) as T;
      }
      return JSON.parse(raw) as T;
    } catch (err) {
      this.outputChannel.appendLine(
        `[drift] Failed to parse response: ${err instanceof Error ? err.message : String(err)}`
      );
      return fallback;
    }
  }
}
