param(
    [Parameter(Mandatory = $true)]
    [string]$OldName,

    [Parameter(Mandatory = $true)]
    [string]$NewName,

    [string]$RepoRoot,
    [string]$CodexHome,
    [switch]$RequireClaudeCopy,
    [switch]$RequireInstalledCopy
)

$ErrorActionPreference = 'Stop'

function Resolve-RequiredPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path $Path)) {
        throw "$Label does not exist: $Path"
    }

    return (Resolve-Path $Path).Path
}

function Get-NormalizedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }

    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $Path))
}

$workspaceRoot = Resolve-RequiredPath -Path (Join-Path $PSScriptRoot '..') -Label 'Workspace root'
$resolvedRepoRoot = if ($PSBoundParameters.ContainsKey('RepoRoot')) {
    Resolve-RequiredPath -Path $RepoRoot -Label 'Repo root'
} else {
    Resolve-RequiredPath -Path (Join-Path (Join-Path $workspaceRoot '..') '..') -Label 'Repo root'
}

$resolvedCodexHome = if ($PSBoundParameters.ContainsKey('CodexHome')) {
    Get-NormalizedPath -Path $CodexHome
} elseif ($env:CODEX_HOME) {
    Get-NormalizedPath -Path $env:CODEX_HOME
} else {
    Get-NormalizedPath -Path (Join-Path $HOME '.codex')
}

$codexSkillsRoot = Join-Path $resolvedCodexHome 'skills'
$repoSkillRoot = Join-Path $resolvedRepoRoot "ops/notion-workspace/skills/$NewName"
$repoOldSkillRoot = Join-Path $resolvedRepoRoot "ops/notion-workspace/skills/$OldName"
$claudeSkillRoot = Join-Path $resolvedRepoRoot ".claude/skills/$NewName"
$claudeOldSkillRoot = Join-Path $resolvedRepoRoot ".claude/skills/$OldName"
$codexSkillRoot = Join-Path $codexSkillsRoot $NewName
$codexOldSkillRoot = Join-Path $codexSkillsRoot $OldName

function Get-OldNameMatches {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SearchTerm,

        [Parameter(Mandatory = $true)]
        [string[]]$Roots
    )

    $rg = Get-Command rg -ErrorAction SilentlyContinue
    if ($rg) {
        $output = & $rg.Source -n -F --hidden `
            --glob '!.git/**' `
            --glob '!.claude/tmp/**' `
            --glob '!ops/notion-workspace/.tmp/**' `
            $SearchTerm @Roots 2>$null

        if ($LASTEXITCODE -eq 0) {
            return @($output)
        }

        if ($LASTEXITCODE -eq 1) {
            return @()
        }

        throw "rg search failed with exit code $LASTEXITCODE"
    }

    $files = Get-ChildItem -Path $Roots -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch '[\\/]\\.git([\\/]|$)' -and
            $_.FullName -notmatch '[\\/]\\.claude[\\/]tmp([\\/]|$)' -and
            $_.FullName -notmatch '[\\/]ops[\\/]notion-workspace[\\/]\\.tmp([\\/]|$)'
        }

    $matches = @()
    foreach ($file in $files) {
        $result = Select-String -Path $file.FullName -SimpleMatch -Pattern $SearchTerm -ErrorAction SilentlyContinue
        foreach ($match in $result) {
            $matches += '{0}:{1}:{2}' -f $file.FullName, $match.LineNumber, $match.Line.Trim()
        }
    }

    return $matches
}

$searchRoots = @($resolvedRepoRoot)
if (Test-Path $codexSkillsRoot) {
    $searchRoots += (Resolve-Path $codexSkillsRoot).Path
}

$issues = New-Object System.Collections.Generic.List[string]
$matches = Get-OldNameMatches -SearchTerm $OldName -Roots $searchRoots

if ($matches.Count -gt 0) {
    $issues.Add("Found lingering matches for '$OldName':")
    foreach ($match in $matches) {
        $issues.Add("  $match")
    }
}

$requiredPaths = @($repoSkillRoot)
if ($RequireClaudeCopy) {
    $requiredPaths += $claudeSkillRoot
}

if ($RequireInstalledCopy) {
    $requiredPaths += $codexSkillRoot
}

foreach ($path in $requiredPaths) {
    if (-not (Test-Path $path)) {
        $issues.Add("Expected renamed path is missing: $path")
    }
}

$retiredPaths = @($repoOldSkillRoot, $claudeOldSkillRoot, $codexOldSkillRoot)
foreach ($path in $retiredPaths) {
    if (Test-Path $path) {
        $issues.Add("Retired path still exists: $path")
    }
}

if ($issues.Count -gt 0) {
    foreach ($issue in $issues) {
        Write-Error $issue
    }

    exit 1
}

Write-Output "Skill rename cleanup OK: '$OldName' -> '$NewName'"
