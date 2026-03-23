param(
    [string[]]$Paths,
    [string[]]$ScopeRoots = @('ops/notion-workspace', '.claude/skills'),
    [switch]$RequireCleanScope
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$repoRoot = Resolve-Path (Join-Path (Join-Path $workspaceRoot '..') '..')

$textExtensions = @(
    '.md', '.txt', '.ps1', '.cmd', '.json', '.yaml', '.yml',
    '.py', '.sql', '.toml', '.xml', '.csv'
)

$mojibakeTokens = @(
    # Common UTF-8 bytes mis-decoded as Windows-1252 punctuation.
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x2013),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x2014),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x201C),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x201D),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x2122),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x0153),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x00A2),
    ([string]([char]0x00E2) + [char]0x20AC + [char]0x00A6),
    ([string]([char]0x00E2) + [char]0x20AC),
    ([string]([char]0x00E2) + [char]0x2020),
    # Emoji and variation-selector fragments that show up after bad re-encoding.
    ([string]([char]0x00F0) + [char]0x0178),
    ([string]([char]0x00EF) + [char]0x00B8),
    [string][char]0xFFFD
)

$gitCommand = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCommand) {
    throw 'Git is required to run test-closeout-sanity.ps1.'
}

try {
    & git -C $repoRoot.Path rev-parse --show-toplevel | Out-Null
} catch {
    throw 'test-closeout-sanity.ps1 must run inside the FreedSolutions git repository.'
}

function Get-RepoRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $fullPath = if ([System.IO.Path]::IsPathRooted($Path)) {
        [System.IO.Path]::GetFullPath($Path)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path $repoRoot.Path $Path))
    }

    $repoPrefix = $repoRoot.Path.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if ($fullPath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $fullPath.Substring($repoPrefix.Length).Replace('\', '/')
    }

    throw "Path is outside the repo root: $Path"
}

function Test-IsInScope {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    foreach ($scopeRoot in $ScopeRoots) {
        $normalizedScope = $scopeRoot.Replace('\', '/').TrimEnd('/')
        if ($RelativePath -eq $normalizedScope -or $RelativePath.StartsWith("$normalizedScope/", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Test-MatchesRequestedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,
        [string[]]$RequestedPaths = @()
    )

    if (-not $RequestedPaths -or $RequestedPaths.Count -eq 0) {
        return $true
    }

    foreach ($requestedPath in $RequestedPaths) {
        $normalizedRequestedPath = $requestedPath.Replace('\', '/').TrimEnd('/')
        if (-not $normalizedRequestedPath) {
            continue
        }
        if ($RelativePath -eq $normalizedRequestedPath -or $RelativePath.StartsWith("$normalizedRequestedPath/", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Get-TrackedChangedRepoPaths {
    $changed = @()
    $changed += @(& git -C $repoRoot.Path diff --name-only --)
    $changed += @(& git -C $repoRoot.Path diff --cached --name-only --)

    return $changed |
        Where-Object { $_ } |
        ForEach-Object { $_.Replace('\', '/') } |
        Select-Object -Unique
}

function Get-UntrackedRepoPaths {
    return @(& git -C $repoRoot.Path ls-files --others --exclude-standard --) |
        Where-Object { $_ } |
        ForEach-Object { $_.Replace('\', '/') } |
        Select-Object -Unique
}

function Test-IsTextPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $extension = [System.IO.Path]::GetExtension($RelativePath)
    return $textExtensions -contains $extension.ToLowerInvariant()
}

$requestedPaths = @()
if ($Paths -and $Paths.Count -gt 0) {
    $requestedPaths = @($Paths | ForEach-Object { Get-RepoRelativePath -Path $_ } | Select-Object -Unique)
}

$explicitRequestedTextPaths = @($requestedPaths |
    Where-Object { Test-IsTextPath -RelativePath $_ } |
    Where-Object { Test-Path (Join-Path $repoRoot.Path $_) -PathType Leaf })

if ($explicitRequestedTextPaths.Count -gt 0) {
    $candidatePaths = $explicitRequestedTextPaths
} else {
    $candidatePaths = @(Get-TrackedChangedRepoPaths |
        Where-Object { Test-MatchesRequestedPath -RelativePath $_ -RequestedPaths $requestedPaths })
}

$scopedPaths = @($candidatePaths | Where-Object { Test-IsInScope -RelativePath $_ })
$existingScopedTextPaths = @($scopedPaths |
    Where-Object { Test-IsTextPath -RelativePath $_ } |
    Where-Object { Test-Path (Join-Path $repoRoot.Path $_) -PathType Leaf })

$untrackedScopedPaths = @(Get-UntrackedRepoPaths |
    Where-Object { Test-IsInScope -RelativePath $_ } |
    Where-Object { Test-MatchesRequestedPath -RelativePath $_ -RequestedPaths $requestedPaths })

$mojibakeRegex = ($mojibakeTokens | ForEach-Object { [regex]::Escape($_) }) -join '|'
$mojibakeHits = New-Object System.Collections.Generic.List[string]

foreach ($relativePath in $existingScopedTextPaths) {
    $fullPath = Join-Path $repoRoot.Path $relativePath
    $fileLines = @(Get-Content -Path $fullPath -Encoding UTF8)
    for ($lineIndex = 0; $lineIndex -lt $fileLines.Count; $lineIndex++) {
        $line = $fileLines[$lineIndex]
        if ($line -match $mojibakeRegex) {
            $mojibakeHits.Add(('{0}:{1}:{2}' -f $relativePath, ($lineIndex + 1), $line.Trim()))
        }
    }
}

if ($mojibakeHits.Count -gt 0) {
    foreach ($hit in $mojibakeHits) {
        Write-Error "Likely mojibake found: $hit"
    }

    exit 1
}

if ($untrackedScopedPaths.Count -gt 0) {
    foreach ($relativePath in $untrackedScopedPaths) {
        if ($RequireCleanScope) {
            Write-Error "Untracked scoped file present: $relativePath"
        } else {
            Write-Warning "Untracked scoped file present: $relativePath"
        }
    }

    if ($RequireCleanScope) {
        exit 1
    }
}

if ($existingScopedTextPaths.Count -eq 0) {
    Write-Output 'Closeout sanity OK: no changed scoped text files to scan.'
    exit 0
}

$scannedCount = $existingScopedTextPaths.Count
if ($untrackedScopedPaths.Count -gt 0) {
    Write-Output "Closeout sanity OK: scanned $scannedCount scoped text file(s); untracked scoped files were reported separately."
} else {
    Write-Output "Closeout sanity OK: scanned $scannedCount scoped text file(s); no mojibake found."
}
