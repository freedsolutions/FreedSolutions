param(
    [string]$ManifestFile,
    [string]$ResultFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'sub-agent-contract-helpers.ps1')

function Get-HashtableFromJsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "JSON file not found: $Path"
    }

    $parsed = Get-Content -Path $Path -Raw -Encoding UTF8 | ConvertFrom-Json
    return ConvertTo-PlainHashtable -Value $parsed
}

function ConvertTo-PlainHashtable {
    param(
        [Parameter(Mandatory = $true)]
        $Value
    )

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $table = @{}
        foreach ($key in $Value.Keys) {
            $table[$key] = ConvertTo-PlainHashtable -Value $Value[$key]
        }
        return $table
    }

    if (
        $Value -isnot [string] -and
        $Value -is [System.Collections.IEnumerable]
    ) {
        $items = New-Object System.Collections.ArrayList
        foreach ($item in $Value) {
            [void]$items.Add((ConvertTo-PlainHashtable -Value $item))
        }
        return @($items)
    }

    if ($Value.PSObject -and $Value.PSObject.Properties.Count -gt 0 -and $Value -isnot [string]) {
        $table = @{}
        foreach ($property in $Value.PSObject.Properties) {
            $table[$property.Name] = ConvertTo-PlainHashtable -Value $property.Value
        }
        return $table
    }

    return $Value
}

function Assert-Throws {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock,

        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    try {
        & $ScriptBlock | Out-Null
    } catch {
        return
    }

    throw "Expected sub-agent contract rejection for: $Label"
}

if ($ManifestFile) {
    $manifest = Get-HashtableFromJsonFile -Path $ManifestFile
    Assert-SubAgentManifest -Manifest $manifest
    Write-Output "Sub-agent contract OK: manifest '$ManifestFile' is valid."
    exit 0
}

if ($ResultFile) {
    $result = Get-HashtableFromJsonFile -Path $ResultFile
    Assert-SubAgentResultEnvelope -Result $result
    Write-Output "Sub-agent contract OK: result envelope '$ResultFile' is valid."
    exit 0
}

$validManifest = @{
    run_id = '2026-03-27T12:00:00-abcd'
    parent_skill = 'notion-active-session'
    delegated_scope = 'Audit launcher baseline'
    gate_ceiling = 'UNGATED'
    read_paths = @('ops/notion-workspace/CLAUDE.md', 'ops/notion-workspace/docs/test-playbooks.md')
    write_paths = @()
    scaffold_profile = 'explorer'
    depth = 1
}

$validHardGateManifest = @{
    run_id = '2026-03-27T12:10:00-efgh'
    parent_skill = 'direct'
    delegated_scope = 'Patch one local skill file'
    gate_ceiling = 'HARDENED_GATE'
    read_paths = @('ops/notion-workspace/skills/notion-active-session/SKILL.md')
    write_paths = @('ops/notion-workspace/skills/notion-active-session/SKILL.md')
    scaffold_profile = 'scaffolding-editor'
    depth = 1
}

$validResult = @{
    run_id = '2026-03-27T12:00:00-abcd'
    status = 'success'
    summary = 'Validated the manifest and collected findings.'
    findings = @()
    mutations_performed = @(
        @{
            target = 'ops/notion-workspace/CLAUDE.md'
            action = 'update'
            detail = 'Documented the baseline validator.'
        }
    )
}

Assert-SubAgentManifest -Manifest $validManifest
Assert-SubAgentManifest -Manifest $validHardGateManifest
Assert-SubAgentParallelWritePaths -Manifests @($validManifest, $validHardGateManifest)
Assert-SubAgentResultEnvelope -Result $validResult

Assert-Throws -Label 'UNGATED manifest with write_paths' -ScriptBlock {
    $invalidManifest = @{
        run_id = '2026-03-27T12:20:00-bad1'
        parent_skill = 'notion-active-session'
        delegated_scope = 'Mutate repo file without a gate'
        gate_ceiling = 'UNGATED'
        read_paths = @('ops/notion-workspace/CLAUDE.md')
        write_paths = @('ops/notion-workspace/CLAUDE.md')
        scaffold_profile = 'explorer'
        depth = 1
    }

    Assert-SubAgentManifest -Manifest $invalidManifest
}

Assert-Throws -Label 'manifest depth greater than one' -ScriptBlock {
    $invalidManifest = @{
        run_id = '2026-03-27T12:21:00-bad2'
        parent_skill = 'notion-active-session'
        delegated_scope = 'Nested delegation'
        gate_ceiling = 'HARDENED_GATE'
        read_paths = @('ops/notion-workspace/CLAUDE.md')
        write_paths = @()
        scaffold_profile = 'explorer'
        depth = 2
    }

    Assert-SubAgentManifest -Manifest $invalidManifest
}

Assert-Throws -Label 'governance gate delegation' -ScriptBlock {
    $invalidManifest = @{
        run_id = '2026-03-27T12:22:00-bad3'
        parent_skill = 'notion-active-session'
        delegated_scope = 'Delegated schema change'
        gate_ceiling = 'GOVERNANCE_GATE'
        read_paths = @('ops/notion-workspace/CLAUDE.md')
        write_paths = @()
        scaffold_profile = 'explorer'
        depth = 1
    }

    Assert-SubAgentManifest -Manifest $invalidManifest
}

Assert-Throws -Label 'overlapping parallel write_paths' -ScriptBlock {
    $overlapA = @{
        run_id = '2026-03-27T12:23:00-a'
        parent_skill = 'notion-active-session'
        delegated_scope = 'Write A'
        gate_ceiling = 'HARDENED_GATE'
        read_paths = @('ops/notion-workspace/CLAUDE.md')
        write_paths = @('ops/notion-workspace/CLAUDE.md')
        scaffold_profile = 'scaffolding-editor'
        depth = 1
    }
    $overlapB = @{
        run_id = '2026-03-27T12:23:00-b'
        parent_skill = 'notion-active-session'
        delegated_scope = 'Write B'
        gate_ceiling = 'HARDENED_GATE'
        read_paths = @('ops/notion-workspace/docs/test-playbooks.md')
        write_paths = @('ops/notion-workspace/CLAUDE.md')
        scaffold_profile = 'scaffolding-editor'
        depth = 1
    }

    Assert-SubAgentParallelWritePaths -Manifests @($overlapA, $overlapB)
}

Assert-Throws -Label 'needs_escalation result without question' -ScriptBlock {
    $invalidResult = @{
        run_id = '2026-03-27T12:24:00-bad4'
        status = 'needs_escalation'
        summary = 'Need a user decision.'
        findings = @()
        mutations_performed = @()
    }

    Assert-SubAgentResultEnvelope -Result $invalidResult
}

Assert-Throws -Label 'failure result without error_detail' -ScriptBlock {
    $invalidResult = @{
        run_id = '2026-03-27T12:25:00-bad5'
        status = 'failure'
        summary = 'The delegation failed.'
        findings = @()
        mutations_performed = @()
    }

    Assert-SubAgentResultEnvelope -Result $invalidResult
}

Write-Output 'Sub-agent contract OK: manifest shape, overlap checks, and result-envelope rules passed.'
