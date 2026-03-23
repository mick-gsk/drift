# Demo Recording Workflow (Vhs)

This folder contains the reproducible terminal demo setup for Drift.

## Files

- `demo.tape`: Vhs script that records core CLI commands.
- `demo.gif`: Rendered artifact used in `README.md`.

## Prerequisites

Install Vhs and its dependencies. On Windows, this is typically easiest via Scoop:

```powershell
scoop install vhs
```

If your setup requires it, install Chrome/Chromium for rendering.

## Render the GIF

Run from repository root:

```powershell
vhs demos/demo.tape
```

Or use the helper script:

```powershell
./scripts/render_demo.ps1
```

The command updates `demos/demo.gif`.

## Keep it deterministic

- Prefer commands that run quickly and produce stable output.
- Avoid machine-specific absolute paths.
- Re-record after major CLI output changes.
