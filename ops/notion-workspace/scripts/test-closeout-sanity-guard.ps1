param(
    [string]$RepoRoot
)

Set-StrictMode -Version Latest
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

$workspaceRoot = Resolve-RequiredPath -Path (Join-Path $PSScriptRoot '..') -Label 'Workspace root'
$resolvedRepoRoot = if ($PSBoundParameters.ContainsKey('RepoRoot')) {
    Resolve-RequiredPath -Path $RepoRoot -Label 'Repo root'
} else {
    Resolve-RequiredPath -Path (Join-Path (Join-Path $workspaceRoot '..') '..') -Label 'Repo root'
}

$closeoutScript = Join-Path $resolvedRepoRoot 'ops/notion-workspace/scripts/test-closeout-sanity.ps1'
$artifactRelativePath = 'ops/notion-workspace/tmp/test-closeout-sanity-staged-tmp.md'
$artifactFullPath = Join-Path $resolvedRepoRoot $artifactRelativePath
$artifactDir = Split-Path -Parent $artifactFullPath
$powerShellCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if (-not $powerShellCommand) {
    $powerShellCommand = Get-Command powershell.exe -ErrorAction Stop
}
$powerShellExe = $powerShellCommand.Source

function Invoke-CloseoutSanity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()

    try {
        $process = Start-Process -FilePath $powerShellExe `
            -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath, '-Paths', 'ops/notion-workspace/scripts/test-closeout-sanity.ps1') `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        $stdout = if (Test-Path $stdoutPath) { Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue } else { '' }
        $stderr = if (Test-Path $stderrPath) { Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue } else { '' }
        $combined = @($stdout, $stderr) -join [Environment]::NewLine

        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            Output   = $combined.Trim()
        }
    }
    finally {
        foreach ($path in @($stdoutPath, $stderrPath)) {
            if (Test-Path $path) {
                Remove-Item -LiteralPath $path -Force
            }
        }
    }
}

if (-not (Test-Path $artifactDir)) {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
}

if (Test-Path $artifactFullPath) {
    throw "Refusing to overwrite existing temp artifact: $artifactRelativePath"
}

$cleanupErrors = New-Object System.Collections.Generic.List[string]

try {
    Set-Content -Path $artifactFullPath -Value '# staged tmp regression artifact' -Encoding UTF8
    & git -C $resolvedRepoRoot add --force -- $artifactRelativePath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to stage test artifact: $artifactRelativePath"
    }

    $stagedArtifact = @(& git -C $resolvedRepoRoot diff --cached --name-only -- $artifactRelativePath)
    if (-not $stagedArtifact -or -not ($stagedArtifact -contains $artifactRelativePath)) {
        throw "Expected test artifact to be staged before invoking closeout sanity: $artifactRelativePath"
    }

    $failureResult = Invoke-CloseoutSanity -ScriptPath $closeoutScript

    if ($failureResult.ExitCode -eq 0) {
        throw 'Expected test-closeout-sanity.ps1 to fail when a tmp artifact is staged, but it passed.'
    }

    $expectedFailure = 'Staged tmp artifact must be unstaged before closeout'
    $normalizedFailureOutput = ($failureResult.Output -replace '\s+', ' ').Trim()
    if (-not $normalizedFailureOutput.Contains($expectedFailure)) {
        throw "Expected failure output containing '$expectedFailure', but saw:`n$($failureResult.Output)"
    }
}
finally {
    if ((& git -C $resolvedRepoRoot diff --cached --name-only -- $artifactRelativePath) -join '') {
        & git -C $resolvedRepoRoot rm --cached --force --quiet -- $artifactRelativePath | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $cleanupErrors.Add("Failed to unstage temp artifact: $artifactRelativePath")
        }
    }

    if (Test-Path $artifactFullPath) {
        Remove-Item -LiteralPath $artifactFullPath -Force
    }
}

if ($cleanupErrors.Count -gt 0) {
    throw ($cleanupErrors -join [Environment]::NewLine)
}

$successResult = Invoke-CloseoutSanity -ScriptPath $closeoutScript

if ($successResult.ExitCode -ne 0) {
    throw "Expected test-closeout-sanity.ps1 to pass after cleanup, but it failed:`n$($successResult.Output)"
}

Write-Output 'test-closeout-sanity staged tmp guard passed.'
