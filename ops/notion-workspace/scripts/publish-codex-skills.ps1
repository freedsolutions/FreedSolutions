param(
    [string[]]$SkillName,
    [string]$InstallRoot,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$sourceRoot = Join-Path $repoRoot "skills"

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

$skills = if ($SkillName -and $SkillName.Count -gt 0) {
    $SkillName
} else {
    Get-ChildItem -Path $sourceRoot -Directory | Select-Object -ExpandProperty Name
}

if (-not $skills) {
    throw "No skills found under $sourceRoot"
}

foreach ($name in $skills) {
    $skillPath = Join-Path $sourceRoot $name
    if (-not (Test-Path $skillPath)) {
        $env:PYTHONPATH = $originalPythonPath
        throw "Skill source not found: $skillPath"
    }

    Write-Host "Validating $name ..."
    python $validator $skillPath
    if ($LASTEXITCODE -ne 0) {
        $env:PYTHONPATH = $originalPythonPath
        throw "Validation failed for $skillPath"
    }
}

if ($ValidateOnly) {
    $env:PYTHONPATH = $originalPythonPath
    Write-Host "Validation complete. No install requested."
    exit 0
}

if (-not (Test-Path $resolvedInstallRoot)) {
    New-Item -ItemType Directory -Path $resolvedInstallRoot | Out-Null
}

foreach ($name in $skills) {
    $skillPath = Join-Path $sourceRoot $name
    $targetPath = Join-Path $resolvedInstallRoot $name

    if (Test-Path $targetPath) {
        Remove-Item -Recurse -Force $targetPath
    }

    Copy-Item -Path $skillPath -Destination $targetPath -Recurse
    Write-Host "Published $name -> $targetPath"
}

$env:PYTHONPATH = $originalPythonPath

Write-Host "Publish complete."
