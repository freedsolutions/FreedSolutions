Set-StrictMode -Version Latest

$script:NotionWorkspaceScriptsRoot = (Resolve-Path $PSScriptRoot).Path
$script:NotionWorkspaceRoot = (Resolve-Path (Join-Path $script:NotionWorkspaceScriptsRoot '..')).Path
$script:NotionWorkspaceRepoRoot = (Resolve-Path (Join-Path $script:NotionWorkspaceRoot '..\..')).Path

function Get-NotionWorkspaceRepoRoot {
    return $script:NotionWorkspaceRepoRoot
}

function Get-NotionWorkspaceRoot {
    return $script:NotionWorkspaceRoot
}

function Resolve-RepoScopedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [string]$RepoRoot = (Get-NotionWorkspaceRepoRoot)
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw 'Path cannot be empty.'
    }

    if ([System.IO.Path]::IsPathRooted($Path)) {
        throw "Absolute paths are not allowed for repo-scoped discovery: $Path"
    }

    $normalizedInput = $Path.Replace('\', '/')
    if ($normalizedInput -match '(^|/)\.\.(/|$)') {
        throw "Path escapes the repo root: $Path"
    }

    $resolvedRepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
    $fullPath = [System.IO.Path]::GetFullPath((Join-Path $resolvedRepoRoot $Path))
    $repoPrefix = $resolvedRepoRoot.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar

    if (
        $fullPath -ne $resolvedRepoRoot -and
        -not $fullPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Resolved path escaped the repo root: $Path"
    }

    if ($fullPath -ne $resolvedRepoRoot) {
        $relativePathForSegments = $fullPath.Substring($repoPrefix.Length)
        $segmentPath = $null
        foreach ($segment in ($relativePathForSegments -split '[\\/]')) {
            if (-not $segment) {
                continue
            }

            $segmentPath = if ($segmentPath) {
                Join-Path $segmentPath $segment
            } else {
                Join-Path $resolvedRepoRoot $segment
            }

            if (Test-Path $segmentPath) {
                $item = Get-Item -LiteralPath $segmentPath -Force
                if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                    throw "Discovery path traverses a reparse point and must be rejected: $Path"
                }
            }
        }
    }

    $relativePath = if ($fullPath -eq $resolvedRepoRoot) {
        ''
    } else {
        $fullPath.Substring($repoPrefix.Length).Replace('\', '/')
    }

    return [pscustomobject]@{
        RepoRoot = $resolvedRepoRoot
        FullPath = $fullPath
        RelativePath = $relativePath
    }
}

