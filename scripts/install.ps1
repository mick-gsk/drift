# Install drift-analyzer on Windows — works in PowerShell 5.1+.
# Usage:
#   irm https://raw.githubusercontent.com/mick-gsk/drift/main/scripts/install.ps1 | iex
#   irm https://raw.githubusercontent.com/mick-gsk/drift/main/scripts/install.ps1 | iex  # then: Install-Drift -Version 2.5.1
#
# This script installs drift-analyzer using the best available Python
# package manager (pipx > uv > pip), creating an isolated environment
# so drift does not interfere with your project dependencies.

function Install-Drift {
    [CmdletBinding()]
    param(
        [string]$Version
    )

    $ErrorActionPreference = "Stop"

    $spec = "drift-analyzer"
    if ($Version) {
        $spec = "drift-analyzer==$Version"
    }

    # --- Detect best installer ---
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        Write-Host "Installing $spec via pipx..."
        pipx install $spec
    }
    elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "Installing $spec via uv tool..."
        uv tool install $spec
    }
    elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        Write-Host "Installing $spec via pip..."
        pip install --user $spec
    }
    elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
        Write-Host "Installing $spec via pip3..."
        pip3 install --user $spec
    }
    else {
        Write-Error @"
No Python package manager found. Install one of:
  - pipx: https://pipx.pypa.io/
  - uv:   https://docs.astral.sh/uv/
  - pip:  https://pip.pypa.io/
"@
        return
    }

    # --- Verify ---
    if (Get-Command drift -ErrorAction SilentlyContinue) {
        Write-Host ""
        $v = & drift --version 2>$null
        Write-Host "drift $v"
        Write-Host ""
        Write-Host "Get started:"
        Write-Host "  drift analyze --repo ."
        Write-Host "  drift explain PFS"
        Write-Host "  drift --help"
    }
    else {
        Write-Host ""
        Write-Host "drift-analyzer was installed but 'drift' is not on your PATH."
        Write-Host "You may need to restart your terminal or add the Scripts directory to PATH."
    }
}

Install-Drift @args
