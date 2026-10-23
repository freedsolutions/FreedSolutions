Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'notion-workspace-helpers.ps1')

$repoRoot = Get-NotionWorkspaceRepoRoot

function Get-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "JSON file not found: $Path"
    }

    return Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Assert-AllowListContains {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$AllowList,

        [Parameter(Mandatory = $true)]
        [string[]]$RequiredEntries,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $missing = @($RequiredEntries | Where-Object { $_ -notin $AllowList })
    if ($missing.Count -gt 0) {
        throw "$Label is missing required allow entries: $($missing -join ', ')"
    }
}

function Assert-AllowListOmits {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$AllowList,

        [Parameter(Mandatory = $true)]
        [string[]]$DisallowedEntries,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $present = @($DisallowedEntries | Where-Object { $_ -in $AllowList })
    if ($present.Count -gt 0) {
        throw "$Label includes disallowed allow entries: $($present -join ', ')"
    }
}

function Invoke-GitCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $stdoutPath = [System.IO.Path]::GetTempFileName()
    $stderrPath = [System.IO.Path]::GetTempFileName()
    $gitArguments = @('-C', $repoRoot) + $Arguments

    try {
        $process = Start-Process -FilePath 'git' `
            -ArgumentList $gitArguments `
            -NoNewWindow `
            -Wait `
            -PassThru `
            -RedirectStandardOutput $stdoutPath `
            -RedirectStandardError $stderrPath

        return @{
            ExitCode = $process.ExitCode
            StdOut = if (Test-Path $stdoutPath) { Get-Content -Path $stdoutPath -Raw -ErrorAction SilentlyContinue } else { '' }
            StdErr = if (Test-Path $stderrPath) { Get-Content -Path $stderrPath -Raw -ErrorAction SilentlyContinue } else { '' }
        }
    }
    finally {
        Remove-Item -LiteralPath $stdoutPath, $stderrPath -Force -ErrorAction SilentlyContinue
    }
}

function Assert-GitTracked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $result = Invoke-GitCheck -Arguments @('ls-files', '--error-unmatch', '--', $RelativePath)
    if ($result.ExitCode -ne 0) {
        throw "Expected repo-tracked Claude baseline file is not tracked: $RelativePath`n$($result.StdErr)$($result.StdOut)"
    }
}

function Assert-GitIgnoredAndUntracked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $trackedResult = Invoke-GitCheck -Arguments @('ls-files', '--error-unmatch', '--', $RelativePath)
    if ($trackedResult.ExitCode -eq 0) {
        throw "Expected workstation-local Claude overlay to stay untracked: $RelativePath"
    }

    $ignoredResult = Invoke-GitCheck -Arguments @('check-ignore', '--quiet', '--', $RelativePath)
    if ($ignoredResult.ExitCode -ne 0) {
        throw "Expected workstation-local Claude overlay to stay git-ignored: $RelativePath`n$($ignoredResult.StdErr)$($ignoredResult.StdOut)"
    }
}

$requiredClaudeAllowEntries = @(
    'Bash(Get-ChildItem *)',
    'Bash(Get-Content *)',
    'Bash(rg *)',
    'Bash(Select-String *)',
    'Bash(grep *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/compare-notion-sync.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/test-compare-notion-sync.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/test-closeout-sanity.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/test-closeout-sanity-guard.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/test-approval-baseline.ps1" *)',
    'Bash(powershell -ExecutionPolicy Bypass -File "ops/notion-workspace/scripts/test-discovery-scope.ps1" *)',
    'Read',
    'Edit',
    'Write',
    'Glob',
    'Grep',
    'WebFetch(domain:localhost)',
    'mcp__notion',
    'mcp__google-workspace',
    'mcp__claude_ai_Notion__notion-fetch',
    'mcp__claude_ai_Notion__notion-search',
    'mcp__claude_ai_Notion__notion-update-page',
    'mcp__claude_ai_Notion__notion-create-pages',
    'mcp__claude_ai_Gmail__gmail_read_message',
    'Agent',
    'TodoWrite'
)

$disallowedRepoClaudeAllowEntries = @(
    'Bash(node -e *)',
    'Bash(NODE_PATH=* node -e *)',
    'Bash(npx serve *)',
    'Bash(npx playwright *)',
    'Bash(npx --version)',
    'Bash(echo *)',
    'Bash(ls *)',
    'Bash(wc *)',
    'Bash(mkdir *)',
    'Bash(pwd)',
    'Bash(which *)'
)

$repoSettingsPath = Join-Path $repoRoot '.claude\settings.json'
$localSettingsPath = Join-Path $repoRoot '.claude\settings.local.json'

$settingsPaths = @($repoSettingsPath)

Assert-GitTracked -RelativePath '.claude/settings.json'
Assert-GitIgnoredAndUntracked -RelativePath '.claude/settings.local.json'

if (Test-Path $localSettingsPath -PathType Leaf) {
    $settingsPaths += $localSettingsPath
}

foreach ($settingsPath in $settingsPaths) {
    $settings = Get-JsonFile -Path $settingsPath
    $allowList = @($settings.permissions.allow)

    Assert-AllowListContains -AllowList $allowList -RequiredEntries $requiredClaudeAllowEntries -Label $settingsPath
}

$repoClaudeSettings = Get-JsonFile -Path $repoSettingsPath
$repoAllowList = @($repoClaudeSettings.permissions.allow)
Assert-AllowListOmits -AllowList $repoAllowList -DisallowedEntries $disallowedRepoClaudeAllowEntries -Label '.claude/settings.json'

$repoAdditionalDirectories = @($repoClaudeSettings.permissions.additionalDirectories)
if ($repoAdditionalDirectories.Count -gt 0) {
    throw '.claude/settings.json must not declare additionalDirectories; keep workstation-only paths in .claude/settings.local.json.'
}

# The repo declares no project MCP servers (the Playwright server was removed 2026-10-23).
# A missing .mcp.json counts as zero servers.
$projectMcpPath = Join-Path $repoRoot '.mcp.json'
$projectMcpServerNames = @()
if (Test-Path $projectMcpPath -PathType Leaf) {
    $projectMcp = Get-JsonFile -Path $projectMcpPath
    if ($null -ne $projectMcp -and $projectMcp.PSObject.Properties['mcpServers'] -and $null -ne $projectMcp.mcpServers) {
        $projectMcpServerNames = @($projectMcp.mcpServers.PSObject.Properties | ForEach-Object { $_.Name })
    }
}
if ($projectMcpServerNames.Count -gt 0) {
    throw ".mcp.json must declare no project MCP servers; found: $($projectMcpServerNames -join ', ')"
}

Write-Output 'Approval baseline OK: Claude settings and project MCP surface match the documented baseline.'
