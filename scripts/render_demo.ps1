$ErrorActionPreference = "Stop"

$repoRoot = Join-Path $PSScriptRoot ".."

# All demo tapes to render (in order)
$tapes = @(
    @{ Tape = "demos/demo.tape";            Gif = "demos/demo.gif";            Label = "hero" },
    @{ Tape = "demos/agent-workflow.tape";  Gif = "demos/agent-workflow.gif";  Label = "agent-workflow" },
    @{ Tape = "demos/trend.tape";           Gif = "demos/trend.gif";           Label = "trend" },
    @{ Tape = "demos/ci-gate.tape";         Gif = "demos/ci-gate.gif";         Label = "ci-gate" },
    @{ Tape = "demos/onboarding.tape";      Gif = "demos/onboarding.gif";      Label = "onboarding" }
)

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

if (Get-Command vhs -ErrorAction SilentlyContinue) {
    Push-Location $repoRoot
    try {
        foreach ($t in $tapes) {
            Write-Host "Rendering $($t.Label) via VHS..."
            vhs $t.Tape
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "VHS failed for $($t.Label) (exit $LASTEXITCODE) — skipping"
            } else {
                Write-Host "  -> $($t.Gif)"
            }
        }
        Write-Host "All demos rendered via VHS."
    }
    finally {
        Pop-Location
    }
} else {
    Write-Host "vhs not found in PATH — using Python (Pillow) renderer for all GIFs."
    Push-Location $repoRoot
    try {
        # Hero GIF (demo.gif)
        Write-Host "Rendering hero (demo.gif)..."
        & $python (Join-Path $repoRoot "scripts\make_demo_gif.py")
        # All four feature GIFs
        Write-Host "Rendering feature GIFs (onboarding, agent-workflow, trend, ci-gate)..."
        & $python (Join-Path $repoRoot "scripts\make_demo_gifs.py")
    }
    finally {
        Pop-Location
    }
}
