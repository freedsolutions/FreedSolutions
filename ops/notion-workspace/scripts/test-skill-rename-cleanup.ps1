param(
    [Parameter(Mandatory = $true)]
    [string]$OldName,

    [Parameter(Mandatory = $true)]
    [string]$NewName,

    [string]$RepoRoot,
    [string]$CodexHome
)

$ErrorActionPreference = 'Stop'

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$resolvedRepoRoot = if ($PSBoundParameters.ContainsKey('RepoRoot')) {
    (Resolve-Path $RepoRoot).Path
} else {
    (Resolve-Path (Join-Path (Join-Path $workspaceRoot '..') '..')).Path
}

$resolvedCodexHome = if ($PSBoundParameters.ContainsKey('CodexHome')) {
    (Resolve-Path $CodexHome).Path
} elseif ($env:CODEX_HOME) {
    $env:CODEX_HOME
} else {
    Join-Path $HOME '.codex'
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

$requiredPaths = @($repoSkillRoot, $claudeSkillRoot, $codexSkillRoot)
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
