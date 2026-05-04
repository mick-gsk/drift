#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fail CI when public-repo hygiene rules are violated.

.DESCRIPTION
    Enforces two repository-level guardrails:

    1. A glob-based blocklist for sensitive or local-only tracked files.
    2. A root-entry allowlist that keeps the repository root intentionally small.

    Port of scripts/check_repo_hygiene.py — no Python interpreter required.
    Glob patterns use PowerShell -like semantics (* matches any sequence
    including path separators), which is equivalent to Python fnmatch on
    POSIX-normalised paths.

    Exit codes:
      0 - all checks passed
      1 - violations found (blocked file or unlisted root entry)
      2 - configuration error (missing or empty config file)

.PARAMETER Config
    Path to the blocklist config file.
    Default: .github/repo-guard.blocklist

.PARAMETER RootAllowlist
    Path to the root-entry allowlist file.
    Default: .github/repo-root-allowlist

.EXAMPLE
    pwsh scripts/check_repo_hygiene.ps1
    pwsh scripts/check_repo_hygiene.ps1 --Config .github/repo-guard.blocklist --RootAllowlist .github/repo-root-allowlist
#>

param(
    [string]$Config = ".github/repo-guard.blocklist",
    [string]$RootAllowlist = ".github/repo-root-allowlist",
    [int]$RootSurfaceBudget = 95,
    [string]$TrendFile = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Read-PatternFile {
    param([string]$Path)
    $entries = [System.Collections.Generic.List[string]]::new()
    foreach ($line in (Get-Content -Path $Path -Encoding utf8)) {
        $trimmed = $line.Trim()
        if ($trimmed -and -not $trimmed.StartsWith('#')) {
            $entries.Add($trimmed)
        }
    }
    return , $entries.ToArray()
}

function Get-GitTrackedFiles {
    $output = & git ls-files 2>&1
    if ($LASTEXITCODE -ne 0) {
        [Console]::Error.WriteLine(">>> [repo-guard] ERROR: Could not list tracked files via git ls-files")
        if ($output) { [Console]::Error.WriteLine($output) }
        exit 2
    }
    # Normalise backslashes and filter empty lines
    return @($output | ForEach-Object { ($_ -replace '\\', '/').Trim() } | Where-Object { $_ })
}

function Find-BlocklistViolations {
    param([string[]]$Files, [string[]]$Patterns)
    $violations = [System.Collections.Generic.List[PSCustomObject]]::new()
    foreach ($file in $Files) {
        foreach ($pattern in $Patterns) {
            # PowerShell -like: * matches any sequence (including /)
            # This is equivalent to Python fnmatch on normalised POSIX paths.
            if ($file -like $pattern) {
                $violations.Add([PSCustomObject]@{ File = $file; Pattern = $pattern })
                break
            }
        }
    }
    return , $violations.ToArray()
}

function Get-TrackedRootEntries {
    param([string[]]$Files)
    $roots = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($file in $Files) {
        $root = $file.Split('/')[0]
        if ($root) { [void]$roots.Add($root) }
    }
    return @($roots | Sort-Object)
}

function Find-AllowlistViolations {
    param([string[]]$RootEntries, [string[]]$AllowlistPatterns)
    $violations = [System.Collections.Generic.List[PSCustomObject]]::new()
    foreach ($entry in $RootEntries) {
        $matched = $false
        foreach ($pattern in $AllowlistPatterns) {
            if ($entry -like $pattern) {
                $matched = $true
                break
            }
        }
        if (-not $matched) {
            $violations.Add([PSCustomObject]@{ Entry = $entry; Pattern = '<no allowlist match>' })
        }
    }
    return , $violations.ToArray()
}

function Get-LatestRootSurfaceEntry {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }

    $latest = $null
    foreach ($line in (Get-Content -Path $Path -Encoding utf8)) {
        $trimmed = $line.Trim()
        if (-not $trimmed) {
            continue
        }
        try {
            $obj = $trimmed | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            continue
        }
        if ($null -ne $obj.root_surface_area) {
            $latest = $obj
        }
    }
    return $latest
}

function Append-RootSurfaceEntry {
    param(
        [string]$Path,
        [int]$RootSurfaceArea,
        [int]$Budget,
        [bool]$BudgetExceeded
    )

    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    $gitSha = ""
    $shaOutput = & git rev-parse --short HEAD 2>$null
    if ($LASTEXITCODE -eq 0 -and $shaOutput) {
        $gitSha = ($shaOutput | Select-Object -First 1).Trim()
    }

    $entry = [ordered]@{
        timestamp = [DateTime]::UtcNow.ToString("o")
        metric = "root_surface_area"
        git_sha = $gitSha
        root_surface_area = $RootSurfaceArea
        budget = $Budget
        budget_exceeded = $BudgetExceeded
    }
    ($entry | ConvertTo-Json -Compress) | Out-File -FilePath $Path -Encoding utf8 -Append
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if (-not (Test-Path $Config)) {
    [Console]::Error.WriteLine(">>> [repo-guard] ERROR: Config not found: $Config")
    exit 2
}

if (-not (Test-Path $RootAllowlist)) {
    [Console]::Error.WriteLine(">>> [repo-guard] ERROR: Root allowlist not found: $RootAllowlist")
    exit 2
}

$patterns = Read-PatternFile -Path $Config
if (-not $patterns -or $patterns.Count -eq 0) {
    [Console]::Error.WriteLine(">>> [repo-guard] ERROR: No patterns configured in $Config")
    exit 2
}

$allowlistPatterns = Read-PatternFile -Path $RootAllowlist
if (-not $allowlistPatterns -or $allowlistPatterns.Count -eq 0) {
    [Console]::Error.WriteLine(">>> [repo-guard] ERROR: No root entries configured in $RootAllowlist")
    exit 2
}

$files = Get-GitTrackedFiles
$violations = Find-BlocklistViolations -Files $files -Patterns $patterns
$rootEntries = Get-TrackedRootEntries -Files $files
$rootViolations = Find-AllowlistViolations -RootEntries $rootEntries -AllowlistPatterns $allowlistPatterns
$rootSurfaceArea = $rootEntries.Count
$budgetExceeded = $rootSurfaceArea -gt $RootSurfaceBudget
$trendDelta = $null

if ($TrendFile) {
    $previous = Get-LatestRootSurfaceEntry -Path $TrendFile
    if ($null -ne $previous -and $null -ne $previous.root_surface_area) {
        $trendDelta = [int]$rootSurfaceArea - [int]$previous.root_surface_area
    }
    Append-RootSurfaceEntry -Path $TrendFile -RootSurfaceArea $rootSurfaceArea -Budget $RootSurfaceBudget -BudgetExceeded $budgetExceeded
}

$hasError = $false

if ($violations.Count -gt 0) {
    $hasError = $true
    Write-Host ">>> [repo-guard] ERROR: Blocked tracked files detected:"
    foreach ($v in $violations) {
        Write-Host " - $($v.File)  (matched: $($v.Pattern))"
    }
    Write-Host ">>> [repo-guard] Remove these files from git history or rename/move them."
}

if ($rootViolations.Count -gt 0) {
    $hasError = $true
    Write-Host ">>> [repo-guard] ERROR: Unexpected tracked root entries detected:"
    foreach ($v in $rootViolations) {
        Write-Host " - $($v.Entry)  (matched: $($v.Pattern))"
    }
    Write-Host ">>> [repo-guard] Move the entry into the appropriate subdirectory or update the allowlist with rationale."
}

if ($budgetExceeded) {
    $hasError = $true
    $over = $rootSurfaceArea - $RootSurfaceBudget
    Write-Host ">>> [repo-guard] ERROR: Root surface area budget exceeded: current=$rootSurfaceArea, budget=$RootSurfaceBudget, over=$over."
}

Write-Host ">>> [repo-guard] Metric: root_surface_area=$rootSurfaceArea (budget=$RootSurfaceBudget)."
if ($null -ne $trendDelta) {
    Write-Host ">>> [repo-guard] Trend: root_surface_area delta vs previous run=$([int]$trendDelta)."
}

if ($hasError) {
    exit 1
}

Write-Host ">>> [repo-guard] OK: Blocklist, root-allowlist, and root-surface budget checks passed."
exit 0
