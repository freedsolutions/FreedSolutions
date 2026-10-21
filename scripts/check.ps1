<#
.SYNOPSIS
    Run every repo check in order. Stop at the first failure.

.DESCRIPTION
    From the repo root (any cwd works; the script moves itself there):

        powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1

    One line per step: PASS or FAIL, the step name, and its time. A failing step prints the
    output it captured, then a one-line summary, and the script exits with that step's exit code.
    -ShowOutput streams every step's output as it runs.

    Steps, in order:
      1. python -m unittest on the three repo test modules (tests/ has no __init__.py, so
         discover cannot find them; the modules are named by path)
      2-8. the seven ops/notion-workspace/scripts/test-*.ps1 checks. test-skill-rename-cleanup.ps1
         takes a rename pair, so it runs on a synthetic one: a retired name minted at run time
         (so no file can contain it) renamed to create-skill, which exists in both the source root
         and the wrapper root
      9. sync-claude-skill-wrappers.ps1 -ValidateOnly: every .claude/skills/ wrapper matches its
         freed-solutions/skills/ source
     10. publish-codex-skills.ps1 -ValidateOnly: every skill source passes the Codex validator
         (needs ~/.codex; this step is the one that cannot run on a CI runner)
     11. bi-change gate_selftest.js
     12. bi-change skill_leak_proof.js --selftest: every leak rule fails on a breaker fixture
     13. bi-change skill_leak_proof.js: no tracked skill file names a client
     14. dutchie-intake selftest_all.py

    No dependencies beyond what the steps already need: Windows PowerShell 5.1, python, node.
    .github/workflows/checks.yml runs steps 1, 11, 12 and 13 on push and pull request.
#>
param(
    [switch]$ShowOutput
)

# Native stderr must not abort the runner; each step's exit code is the verdict.
$ErrorActionPreference = 'Continue'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

# Child processes write UTF-8 (the intake self-test prints arrows and dashes); decode it as such.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

$powershell = (Get-Command powershell -ErrorAction Stop).Source
$workspaceScripts = 'ops/notion-workspace/scripts'

function New-Step {
    param(
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string[]]$Command
    )
    return @{ Name = $Name; Command = $Command }
}

function New-PsStep {
    param(
        [Parameter(Mandatory = $true)] [string]$Name,
        [Parameter(Mandatory = $true)] [string]$Script,
        [string[]]$Arguments = @()
    )
    $command = @($powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', $Script) + $Arguments
    return New-Step -Name $Name -Command $command
}

# A name no file can contain: the rename test greps the whole repo for it and must find nothing.
$retiredSkillName = 'retired-skill-' + [guid]::NewGuid().ToString('N')

$steps = @(
    (New-Step 'python unittest: test_codex_review, test_local_db, test_closeout_sanity' @(
        'python', '-m', 'unittest',
        'tests/test_codex_review.py', 'tests/test_local_db.py', 'tests/test_closeout_sanity.py')),
    (New-PsStep 'test-approval-baseline.ps1' "$workspaceScripts/test-approval-baseline.ps1"),
    (New-PsStep 'test-closeout-sanity-guard.ps1' "$workspaceScripts/test-closeout-sanity-guard.ps1"),
    (New-PsStep 'test-closeout-sanity.ps1' "$workspaceScripts/test-closeout-sanity.ps1"),
    (New-PsStep 'test-compare-notion-sync.ps1' "$workspaceScripts/test-compare-notion-sync.ps1"),
    (New-PsStep 'test-discovery-scope.ps1' "$workspaceScripts/test-discovery-scope.ps1"),
    (New-PsStep 'test-save-notion-sync-remote.ps1' "$workspaceScripts/test-save-notion-sync-remote.ps1"),
    (New-PsStep 'test-skill-rename-cleanup.ps1 (synthetic retired name -> create-skill)' "$workspaceScripts/test-skill-rename-cleanup.ps1" @(
        '-OldName', $retiredSkillName, '-NewName', 'create-skill', '-RequireClaudeCopy')),
    (New-PsStep 'sync-claude-skill-wrappers.ps1 -ValidateOnly' "$workspaceScripts/sync-claude-skill-wrappers.ps1" @('-ValidateOnly')),
    (New-PsStep 'publish-codex-skills.ps1 -ValidateOnly' "$workspaceScripts/publish-codex-skills.ps1" @('-ValidateOnly')),
    (New-Step 'bi-change gate_selftest.js' @('node', '.claude/skills/bi-change/scripts/gate_selftest.js')),
    (New-Step 'bi-change skill_leak_proof.js --selftest' @('node', '.claude/skills/bi-change/scripts/skill_leak_proof.js', '--selftest')),
    (New-Step 'bi-change skill_leak_proof.js' @('node', '.claude/skills/bi-change/scripts/skill_leak_proof.js')),
    (New-Step 'dutchie-intake selftest_all.py' @('python', '.claude/skills/dutchie-intake/scripts/selftest_all.py'))
)

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)] [hashtable]$Step
    )

    $exe = $Step.Command[0]
    $arguments = @()
    if ($Step.Command.Count -gt 1) {
        $arguments = $Step.Command[1..($Step.Command.Count - 1)]
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $global:LASTEXITCODE = 0

    try {
        $resolved = Get-Command $exe -ErrorAction Stop
        & $resolved.Source @arguments 2>&1 | ForEach-Object {
            $line = if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.Exception.Message } else { [string]$_ }
            $lines.Add($line)
            if ($ShowOutput) { Write-Host "    $line" }
        }
        $exitCode = $LASTEXITCODE
    } catch {
        $lines.Add($_.Exception.Message)
        $exitCode = 127
    }

    $stopwatch.Stop()
    return @{
        ExitCode = $exitCode
        Seconds  = [math]::Round($stopwatch.Elapsed.TotalSeconds, 1)
        Output   = $lines
    }
}

$total = $steps.Count
$runStopwatch = [System.Diagnostics.Stopwatch]::StartNew()

for ($i = 0; $i -lt $total; $i++) {
    $step = $steps[$i]
    $label = '[{0,2}/{1}]' -f ($i + 1), $total
    if ($ShowOutput) { Write-Host "$label RUN   $($step.Name)" }

    $result = Invoke-Step -Step $step

    if ($result.ExitCode -eq 0) {
        Write-Host ('{0} PASS  {1}  ({2}s)' -f $label, $step.Name, $result.Seconds) -ForegroundColor Green
        continue
    }

    Write-Host ('{0} FAIL  {1}  (exit {2}, {3}s)' -f $label, $step.Name, $result.ExitCode, $result.Seconds) -ForegroundColor Red
    if (-not $ShowOutput) {
        Write-Host '--- step output ---'
        foreach ($line in $result.Output) { Write-Host "    $line" }
        Write-Host '--- end of step output ---'
    }
    Write-Host ('check.ps1: FAILED at step {0} of {1} ({2}), exit {3}. Steps after it did not run.' -f ($i + 1), $total, $step.Name, $result.ExitCode) -ForegroundColor Red
    exit $result.ExitCode
}

$runStopwatch.Stop()
Write-Host ('check.ps1: all {0} steps passed in {1}s.' -f $total, [math]::Round($runStopwatch.Elapsed.TotalSeconds, 1)) -ForegroundColor Green
exit 0
