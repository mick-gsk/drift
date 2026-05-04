#!/usr/bin/env pwsh
# List all skills under .github/skills/ with their dependency classification.
# Skills that declare `dependency: hard|soft` in YAML frontmatter are shown
# under the matching group. Skills without the field are listed as "unclassified".
#
# Usage:
#   .\scripts\list-skills.ps1
#   .\scripts\list-skills.ps1 --filter hard

param(
    [ValidateSet("hard", "soft", "unclassified", "all")]
    [string]$Filter = "all"
)

$root = Split-Path -Parent $PSScriptRoot
$skillsDir = Join-Path $root ".github\skills"

$hard   = [System.Collections.Generic.List[string]]::new()
$soft   = [System.Collections.Generic.List[string]]::new()
$none   = [System.Collections.Generic.List[string]]::new()

Get-ChildItem -Path $skillsDir -Recurse -Filter "SKILL.md" | Sort-Object FullName | ForEach-Object {
    $skillName = Split-Path -Leaf (Split-Path -Parent $_.FullName)
    $content   = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue

    # Parse YAML frontmatter (--- ... ---)
    $dep = $null
    if ($content -match "(?s)^---\s*\n(.*?)\n---") {
        $frontmatter = $Matches[1]
        if ($frontmatter -match "(?m)^dependency:\s*(\w+)") {
            $dep = $Matches[1].Trim().ToLower()
        }
    }

    switch ($dep) {
        "hard"  { $hard.Add($skillName) }
        "soft"  { $soft.Add($skillName) }
        default { $none.Add($skillName) }
    }
}

function Write-Group {
    param([string]$Label, [string]$Color, [System.Collections.Generic.List[string]]$Items)
    Write-Host "`n$Label ($($Items.Count))" -ForegroundColor $Color
    if ($Items.Count -eq 0) {
        Write-Host "  (none)" -ForegroundColor DarkGray
    } else {
        foreach ($item in $Items) {
            Write-Host "  $item"
        }
    }
}

if ($Filter -eq "all" -or $Filter -eq "hard") {
    Write-Group "HARD dependency" "Red" $hard
}
if ($Filter -eq "all" -or $Filter -eq "soft") {
    Write-Group "SOFT dependency" "Yellow" $soft
}
if ($Filter -eq "all" -or $Filter -eq "unclassified") {
    Write-Group "UNCLASSIFIED (no dependency: field)" "DarkGray" $none
}

$total = $hard.Count + $soft.Count + $none.Count
Write-Host "`nTotal: $total skills" -ForegroundColor Cyan
