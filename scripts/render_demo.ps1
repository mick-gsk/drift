$ErrorActionPreference = "Stop"

if (-not (Get-Command vhs -ErrorAction SilentlyContinue)) {
    Write-Error "Vhs was not found in PATH. Install it first (e.g. 'scoop install vhs')."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
    vhs demos/demo.tape
    Write-Host "Demo rendered to demos/demo.gif"
}
finally {
    Pop-Location
}
