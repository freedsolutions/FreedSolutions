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

function Get-CodexConfigPath {
    if ($env:CODEX_HOME) {
        return Join-Path $env:CODEX_HOME 'config.toml'
    }

    return Join-Path $HOME '.codex\config.toml'
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

function Get-TomlSections {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Leaf)) {
        throw "TOML file not found: $Path"
    }

    $sections = @{}
    $currentSection = $null

    foreach ($rawLine in Get-Content -Path $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#')) {
            continue
        }

        if ($line -match '^\[(?<section>[^\]]+)\]\s*$') {
            $currentSection = $matches.section
            if (-not $sections.ContainsKey($currentSection)) {
                $sections[$currentSection] = @{}
            }
            continue
        }

        if (-not $currentSection) {
            continue
        }

        if ($line -match '^(?<key>[A-Za-z0-9_.-]+)\s*=\s*(?<value>.+?)\s*$') {
            $value = $matches.value.Trim()
            if (
                $value.Length -ge 2 -and
                $value.StartsWith('"') -and
                $value.EndsWith('"')
            ) {
                $value = $value.Substring(1, $value.Length - 2)
            }

            $sections[$currentSection][$matches.key] = $value
        }
    }

    return $sections
}

function Get-CodexProfileSettings {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProfileName,

        [string]$ConfigPath = (Get-CodexConfigPath)
    )

    $sections = Get-TomlSections -Path $ConfigPath
    $sectionName = "profiles.$ProfileName"

    if (-not $sections.ContainsKey($sectionName)) {
        return $null
    }

    return $sections[$sectionName]
}
