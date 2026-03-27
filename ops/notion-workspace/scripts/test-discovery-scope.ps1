param(
    [string]$DiscoveryPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'notion-workspace-helpers.ps1')

$repoRoot = Get-NotionWorkspaceRepoRoot

if ($DiscoveryPath) {
    $resolved = Resolve-RepoScopedPath -Path $DiscoveryPath -RepoRoot $repoRoot
    Write-Output "Discovery scope OK: '$DiscoveryPath' resolves to '$($resolved.RelativePath)'."
    exit 0
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

    throw "Expected discovery-scope rejection for: $Label"
}

$validRepoRoot = Resolve-RepoScopedPath -Path 'ops/notion-workspace' -RepoRoot $repoRoot
if ($validRepoRoot.RelativePath -ne 'ops/notion-workspace') {
    throw 'Repo-scoped discovery did not preserve the expected relative path for ops/notion-workspace.'
}

$validFile = Resolve-RepoScopedPath -Path 'ops/notion-workspace/docs/test-playbooks.md' -RepoRoot $repoRoot
if ($validFile.RelativePath -ne 'ops/notion-workspace/docs/test-playbooks.md') {
    throw 'Repo-scoped discovery did not preserve the expected relative path for docs/test-playbooks.md.'
}

Assert-Throws -Label 'absolute repo path' -ScriptBlock {
    Resolve-RepoScopedPath -Path $repoRoot -RepoRoot $repoRoot
}

Assert-Throws -Label 'parent-directory escape' -ScriptBlock {
    Resolve-RepoScopedPath -Path '..\outside' -RepoRoot $repoRoot
}

$reparsePoint = Get-ChildItem -Path $repoRoot -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue |
    Select-Object -First 1

if ($reparsePoint) {
    Assert-Throws -Label "reparse-point path $($reparsePoint.FullName)" -ScriptBlock {
        $relative = $reparsePoint.FullName.Substring($repoRoot.Length).TrimStart('\')
        Resolve-RepoScopedPath -Path $relative -RepoRoot $repoRoot | Out-Null
    }
} else {
    Write-Output 'Discovery scope note: no local reparse-point fixture found; symlink rejection check skipped.'
}

Write-Output 'Discovery scope OK: relative repo paths resolve, and absolute or escaping discovery paths are rejected.'
