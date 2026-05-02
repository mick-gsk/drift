# Drift — VS Code Extension (Beta)

Inline architectural-drift detection for VS Code, powered by the
[drift-analyzer](https://github.com/mick-gsk/drift) MCP server.

## Features

| Feature | Description |
|---------|-------------|
| **Status Bar Score** | Shows the current composite drift score and a finding summary. |
| **Inline Diagnostics** | Findings from `drift_scan` appear as squigglies directly in the editor. |
| **Analyze Workspace** | Full scan of the repository root — accessible via the Command Palette. |
| **Nudge Current File** | Fast directional feedback (improving / stable / degrading) after an edit — calls `drift_nudge` which takes ~0.2 s. |
| **Browse Findings** | Quick-pick list of all current findings with direct navigation. |

## Requirements

- **drift-analyzer ≥ 2.38.0** installed in the Python environment for this workspace.
- A `drift.yaml` or `.drift.yaml` file in the workspace root (the extension
  activates only when one of these is detected).

## Installation (Beta)

The extension is not yet published to the VS Code Marketplace.
Install it locally from a `.vsix` file:

```bash
# Build the VSIX (requires node/npm in extensions/vscode-drift/)
cd extensions/vscode-drift
npm install
npm run compile
npm run package    # produces vscode-drift-<version>.vsix
```

Then in VS Code: **Extensions → ⋯ → Install from VSIX…** and select the file.

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `drift.pythonPath` | `""` | Path to the Python interpreter with drift-analyzer installed. Leave empty to use the workspace `.venv`. |
| `drift.analyzeOnSave` | `false` | Automatically run Nudge Current File on every file save (requires a prior Analyze Workspace). |
| `drift.maxFindings` | `50` | Maximum findings returned by Analyze Workspace. |
| `drift.serverStartupTimeoutMs` | `10000` | Milliseconds to wait for the Drift MCP server to start. |

## Commands

All commands are available via the Command Palette (`Ctrl+Shift+P` / `⌘⇧P`):

| Command | Description |
|---------|-------------|
| `Drift: Analyze Workspace` | Run a full scan and populate diagnostics. |
| `Drift: Nudge Current File` | Fast directional feedback for the active file. |
| `Drift: Show Findings` | Browse all current findings and navigate to them. |
| `Drift: Clear Diagnostics` | Remove all Drift diagnostics from the editor. |

## How It Works

The extension starts the Drift MCP server as a local stdio child process
(`python -m drift mcp --serve`) and communicates via the
[Model Context Protocol](https://modelcontextprotocol.io/).
No analysis logic lives in the extension itself — all results come from
the server.

```
VS Code Extension (TypeScript)
        │
        │  JSON-RPC over stdio (MCP)
        ▼
Drift MCP Server (Python)
   drift_scan / drift_nudge
```

## Known Limitations

- **Requires a prior scan.** `Drift: Nudge Current File` needs an existing
  drift baseline created by at least one `Drift: Analyze Workspace` run.
- **Python/TypeScript files only.** Drift currently analyses Python (and
  partially TypeScript) files. Other languages are not scored.
- **Single workspace folder.** Multi-root workspaces use the first folder
  as the repository root.
- **No Marketplace release yet.** Install via `.vsix` until the Beta is
  validated.

## Supported Drift Versions

| Drift Version | Supported |
|---------------|-----------|
| ≥ 2.38.0      | Yes       |
| < 2.38.0      | No (MCP interface not stable) |

## License

MIT — see [LICENSE](../../LICENSE).
