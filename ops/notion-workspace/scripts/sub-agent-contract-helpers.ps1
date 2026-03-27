Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot 'notion-workspace-helpers.ps1')

function Test-IsNotionReference {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    if ($Value -match '^(collection|discussion|notion)://') {
        return $true
    }

    if ($Value -match '^https?://') {
        return $true
    }

    if ($Value -match '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$') {
        return $true
    }

    return $false
}

function Get-NormalizedContractTarget {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Target
    )

    if (Test-IsNotionReference -Value $Target) {
        return "notion::$($Target.ToLowerInvariant())"
    }

    $resolved = Resolve-RepoScopedPath -Path $Target
    return "repo::$($resolved.RelativePath.ToLowerInvariant())"
}

function Assert-SubAgentManifest {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Manifest
    )

    $requiredFields = @(
        'run_id',
        'parent_skill',
        'delegated_scope',
        'gate_ceiling',
        'read_paths',
        'write_paths',
        'scaffold_profile',
        'depth'
    )

    foreach ($field in $requiredFields) {
        if (-not $Manifest.ContainsKey($field)) {
            throw "Delegation manifest is missing required field '$field'."
        }
    }

    if ($Manifest.gate_ceiling -notin @('UNGATED', 'HARDENED_GATE')) {
        throw "Delegation manifest has invalid gate_ceiling '$($Manifest.gate_ceiling)'."
    }

    if ([int]$Manifest.depth -ne 1) {
        throw "Delegation manifest depth must equal 1. Found '$($Manifest.depth)'."
    }

    if ($Manifest.read_paths -isnot [System.Collections.IEnumerable]) {
        throw 'Delegation manifest read_paths must be an array.'
    }

    if ($Manifest.write_paths -isnot [System.Collections.IEnumerable]) {
        throw 'Delegation manifest write_paths must be an array.'
    }

    $writeTargets = @($Manifest.write_paths | ForEach-Object { [string]$_ } | Where-Object { $_ })
    if ($Manifest.gate_ceiling -eq 'UNGATED' -and $writeTargets.Count -gt 0) {
        throw 'UNGATED sub-agents must not declare write_paths.'
    }

    foreach ($path in @($Manifest.read_paths) + $writeTargets) {
        $value = [string]$path
        if (-not $value) {
            continue
        }

        [void](Get-NormalizedContractTarget -Target $value)
    }
}

function Assert-SubAgentParallelWritePaths {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Manifests
    )

    $seenTargets = @{}

    foreach ($manifest in $Manifests) {
        $writeTargets = @($manifest.write_paths | ForEach-Object { [string]$_ } | Where-Object { $_ })
        foreach ($target in $writeTargets) {
            $normalizedTarget = Get-NormalizedContractTarget -Target $target
            if ($seenTargets.ContainsKey($normalizedTarget)) {
                throw "Parallel sub-agent write_paths overlap on '$target'."
            }

            $seenTargets[$normalizedTarget] = $true
        }
    }
}

function Assert-SubAgentResultEnvelope {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$Result
    )

    $requiredFields = @('run_id', 'status', 'summary', 'findings', 'mutations_performed')
    foreach ($field in $requiredFields) {
        if (-not $Result.ContainsKey($field)) {
            throw "Sub-agent result envelope is missing required field '$field'."
        }
    }

    if ($Result.status -notin @('success', 'failure', 'needs_escalation', 'timeout')) {
        throw "Sub-agent result envelope has invalid status '$($Result.status)'."
    }

    if ($Result.findings -isnot [System.Collections.IEnumerable]) {
        throw 'Sub-agent result envelope findings must be an array.'
    }

    if ($Result.mutations_performed -isnot [System.Collections.IEnumerable]) {
        throw 'Sub-agent result envelope mutations_performed must be an array.'
    }

    foreach ($mutation in @($Result.mutations_performed)) {
        if ($mutation -isnot [hashtable] -and $mutation -isnot [System.Collections.Specialized.OrderedDictionary]) {
            throw 'Each mutation entry must be an object.'
        }

        foreach ($field in @('target', 'action', 'detail')) {
            if (-not $mutation.Contains($field) -or [string]::IsNullOrWhiteSpace([string]$mutation[$field])) {
                throw "Mutation entry is missing required field '$field'."
            }
        }

        if ([string]$mutation.action -notin @('create', 'update', 'delete')) {
            throw "Mutation action '$($mutation.action)' is invalid."
        }
    }

    if ($Result.status -eq 'needs_escalation' -and [string]::IsNullOrWhiteSpace([string]$Result.escalation_question)) {
        throw 'needs_escalation results must include escalation_question.'
    }

    if ($Result.status -eq 'failure' -and [string]::IsNullOrWhiteSpace([string]$Result.error_detail)) {
        throw 'failure results must include error_detail.'
    }
}
