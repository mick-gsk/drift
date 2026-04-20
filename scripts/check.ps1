#!/usr/bin/env pwsh
# check.ps1 — Windows wrapper for `make check`
# Usage: .\scripts\check.ps1 [make-target]
#
# Runs the specified make target (default: check) inside Git Bash,
# which provides grep/awk/sed and the venv tools needed by the Makefile.
#
# Examples:
#   .\scripts\check.ps1           # full check (lint + typecheck + test + self-analysis)
#   .\scripts\check.ps1 test-fast # only fast unit tests
#   .\scripts\check.ps1 lint      # only lint

param(
    [string]$Target = "check"
)

$gitBash = "C:\Program Files\Git\bin\bash.exe"

if (-not (Test-Path $gitBash)) {
    Write-Error "Git Bash not found at '$gitBash'. Please install Git for Windows."
    exit 1
}

$repoRoot = Split-Path $PSScriptRoot -Parent

# Convert Windows path to POSIX path for Git Bash: C:\foo\bar -> /c/foo/bar
$drive    = $repoRoot.Substring(0, 1).ToLower()
$rest     = $repoRoot.Substring(2) -replace '\\', '/'
$bashPath = "/$drive$rest"

Write-Host ">>> Running: make $Target (via Git Bash)" -ForegroundColor Cyan
& $gitBash -c "cd '$bashPath' && make $Target"
exit $LASTEXITCODE
