param(
    [string[]]$SkillName,
    [string]$InstallRoot,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$repoRoot = Resolve-Path (Join-Path (Join-Path $workspaceRoot "..") "..")
# Skill source roots, in order. Must match sync-claude-skill-wrappers.ps1.
$sourceRoots = @(
    (Join-Path $workspaceRoot "skills"),
    (Join-Path $repoRoot "freed-solutions/skills")
) | Where-Object { Test-Path $_ }

function Get-SkillSourcePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [object[]]$Roots
    )

    foreach ($root in $Roots) {
        $candidate = Join-Path $root $Name
        if (Test-Path (Join-Path $candidate "SKILL.md")) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $null
}

$codexHome = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
} else {
    Join-Path $HOME ".codex"
}

$resolvedInstallRoot = if ($PSBoundParameters.ContainsKey("InstallRoot")) {
    $InstallRoot
} else {
    Join-Path $codexHome "skills"
}

$validator = Join-Path $codexHome "skills/.system/skill-creator/scripts/quick_validate.py"

if (-not (Test-Path $validator)) {
    throw "Skill validator not found at $validator"
}

$shimRoot = Join-Path $PSScriptRoot "python-shims"
if (-not (Test-Path $shimRoot)) {
    throw "Cannot find Python shim directory at $shimRoot"
}

$originalPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($originalPythonPath) {
    "$shimRoot;$originalPythonPath"
} else {
    $shimRoot
}

# The Codex-owned validator calls Path.read_text() with no encoding argument, so
# Python falls back to the locale encoding - cp1252 on this workstation. SKILL.md
# files are UTF-8, so any byte that cp1252 leaves undefined (0x81, 0x8D, 0x8F,
# 0x90, 0x9D) aborts validation with UnicodeDecodeError, and the bytes cp1252 does
# map decode to mojibake (an em-dash arrives as "a EUR ..."). PYTHONUTF8=1 puts the
# interpreter in UTF-8 mode so the default encoding is UTF-8 and the file is read
# as written. We cannot fix this in the validator: it lives under ~/.codex and
# Codex may overwrite it.
$originalPythonUtf8 = $env:PYTHONUTF8
$env:PYTHONUTF8 = "1"

function Restore-PythonEnv {
    $env:PYTHONPATH = $script:originalPythonPath
    $env:PYTHONUTF8 = $script:originalPythonUtf8
}

$skills = if ($SkillName -and $SkillName.Count -gt 0) {
    $SkillName
} else {
    $discovered = @()
    $collisions = @{}
    foreach ($root in $sourceRoots) {
        $names = Get-ChildItem -Path $root -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
            Select-Object -ExpandProperty Name
        foreach ($n in $names) {
            if ($discovered -contains $n) {
                $collisions[$n] = $true
            } else {
                $discovered += $n
            }
        }
    }
    if ($collisions.Count -gt 0) {
        $collided = ($collisions.Keys | Sort-Object) -join ", "
        Restore-PythonEnv
        throw "Skill name collision across source roots: $collided. Rename or consolidate."
    }
    $discovered
}

if (-not $skills) {
    throw "No skills found under any of: $($sourceRoots -join ', ')"
}

foreach ($name in $skills) {
    $skillPath = Get-SkillSourcePath -Name $name -Roots $sourceRoots
    if (-not $skillPath) {
        Restore-PythonEnv
        throw "Skill source not found: $name"
    }

    Write-Host "Validating $name ..."
    python $validator $skillPath
    if ($LASTEXITCODE -ne 0) {
        Restore-PythonEnv
        throw "Validation failed for $skillPath"
    }
}

if ($ValidateOnly) {
    Restore-PythonEnv
    Write-Host "Validation complete. No install requested."
    exit 0
}

if (-not (Test-Path $resolvedInstallRoot)) {
    New-Item -ItemType Directory -Path $resolvedInstallRoot | Out-Null
}

foreach ($name in $skills) {
    $skillPath = Get-SkillSourcePath -Name $name -Roots $sourceRoots
    if (-not $skillPath) {
        Restore-PythonEnv
        throw "Skill source not found during publish: $name"
    }
    $targetPath = Join-Path $resolvedInstallRoot $name

    if (Test-Path $targetPath) {
        Remove-Item -Recurse -Force $targetPath
    }

    Copy-Item -Path $skillPath -Destination $targetPath -Recurse
    Write-Host "Published $name -> $targetPath"
}

Restore-PythonEnv

Write-Host "Publish complete."
