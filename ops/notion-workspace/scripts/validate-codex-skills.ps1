param(
    [string]$SkillsRoot = (Join-Path $PSScriptRoot "..\skills")
)

$ErrorActionPreference = "Stop"

$codexHome = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
} else {
    Join-Path $HOME ".codex"
}

$validator = Join-Path $codexHome "skills\.system\skill-creator\scripts\quick_validate.py"
if (-not (Test-Path $validator)) {
    throw "Cannot find quick_validate.py at $validator"
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

$skillDirs = Get-ChildItem -Path $SkillsRoot -Directory | Sort-Object Name
if (-not $skillDirs) {
    throw "No skill directories found under $SkillsRoot"
}

foreach ($skillDir in $skillDirs) {
    Write-Host "Validating $($skillDir.Name)..."
    python $validator $skillDir.FullName
    if ($LASTEXITCODE -ne 0) {
        $env:PYTHONPATH = $originalPythonPath
        throw "Validation failed for $($skillDir.FullName)"
    }
}

$env:PYTHONPATH = $originalPythonPath

Write-Host "Validated $($skillDirs.Count) skill(s)."
