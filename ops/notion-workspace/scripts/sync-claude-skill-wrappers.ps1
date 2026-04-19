param(
    [string[]]$SkillName,
    [string]$WrapperRoot,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$repoRoot = Resolve-Path (Join-Path (Join-Path $workspaceRoot "..") "..")
# Skill source roots, in order. A skill directory with a SKILL.md under any of these is a valid source.
# Adding a new root: append here and every downstream consumer (publish-codex-skills.ps1) picks it up.
$sourceRoots = @(
    (Join-Path $workspaceRoot "skills"),
    (Join-Path $repoRoot "freed-solutions/skills")
) | Where-Object { Test-Path $_ }

$resolvedWrapperRoot = if ($PSBoundParameters.ContainsKey("WrapperRoot")) {
    $WrapperRoot
} else {
    Join-Path (Join-Path $repoRoot ".claude") "skills"
}

function Get-SkillNames {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    Get-ChildItem -Path $Root -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        Select-Object -ExpandProperty Name
}

function Get-SkillSourcePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [object[]]$Roots
    )

    foreach ($root in $Roots) {
        $candidate = Join-Path $root $Name
        if (Test-Path (Join-Path $candidate "SKILL.md")) {
            return (Resolve-Path $candidate).Path
        }
    }
    return $null
}

function Get-SkillRelativeFromRepoRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SkillPath,
        [Parameter(Mandatory = $true)]
        [string]$RepoRootPath
    )

    $rel = $SkillPath.Substring($RepoRootPath.Length).TrimStart('\', '/').Replace('\', '/')
    return $rel
}

function Get-ClaudeSkillCopyContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceFile,

        [Parameter(Mandatory = $true)]
        [string]$SkillRepoRelative,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $raw = Get-Content -Path $SourceFile -Raw -Encoding UTF8
    $newline = if ($raw -match "`r`n") { "`r`n" } else { "`n" }
    $sourcePath = "$SkillRepoRelative/$RelativePath".Replace('\', '/')
    $message = "Generated from `"$sourcePath`". Edit the repo skill source and rerun `ops/notion-workspace/scripts/sync-claude-skill-wrappers.ps1`; do not edit this Claude copy directly."
    $banner = switch ([System.IO.Path]::GetExtension($RelativePath).ToLowerInvariant()) {
        ".md" { "<!-- $message -->" }
        ".yaml" { "# $message" }
        ".yml" { "# $message" }
        default { $null }
    }

    if (-not $banner) {
        return $raw
    }

    $frontmatterMatch = [regex]::Match($raw, '^(---\r?\n.*?\r?\n---)(\r?\n)?(?<body>[\s\S]*)$', [System.Text.RegularExpressions.RegexOptions]::Singleline)

    if ($RelativePath -eq "SKILL.md" -and $frontmatterMatch.Success) {
        $frontmatter = $frontmatterMatch.Groups[1].Value
        $body = $frontmatterMatch.Groups["body"].Value.TrimStart("`r", "`n")
        return $frontmatter + $newline + $newline + $banner + $newline + $newline + $body
    }

    return $banner + $newline + $newline + $raw.TrimStart("`r", "`n")
}

function Get-RelativeFileMap {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    if (-not (Test-Path $Root)) {
        return @{}
    }

    $resolvedRoot = (Resolve-Path $Root).Path
    $files = Get-ChildItem -Path $resolvedRoot -Recurse -File
    $map = @{}

    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\', '/')
        $map[$relativePath.Replace('\', '/')] = $file.FullName
    }

    return $map
}

function Test-DirectoryMatchesSource {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDir,

        [Parameter(Mandatory = $true)]
        [string]$TargetDir,

        [Parameter(Mandatory = $true)]
        [string]$SkillRepoRelative
    )

    if (-not (Test-Path $TargetDir)) {
        return $false
    }

    $sourceFiles = Get-RelativeFileMap -Root $SourceDir
    $targetFiles = Get-RelativeFileMap -Root $TargetDir

    if ($sourceFiles.Count -ne $targetFiles.Count) {
        return $false
    }

    foreach ($relativePath in $sourceFiles.Keys) {
        if (-not $targetFiles.ContainsKey($relativePath)) {
            return $false
        }

        if ($relativePath -eq "SKILL.md" -or $relativePath -match '\.(md|ya?ml)$') {
            $expectedContent = Get-ClaudeSkillCopyContent -SourceFile $sourceFiles[$relativePath] -SkillRepoRelative $SkillRepoRelative -RelativePath $relativePath
            $actualContent = Get-Content -Path $targetFiles[$relativePath] -Raw -Encoding UTF8
            $normalizedExpected = $expectedContent -replace "\r\n", "`n"
            $normalizedActual = $actualContent -replace "\r\n", "`n"

            if ($normalizedExpected -ne $normalizedActual) {
                return $false
            }
        } else {
            $sourceHash = (Get-FileHash -Algorithm SHA256 -Path $sourceFiles[$relativePath]).Hash
            $targetHash = (Get-FileHash -Algorithm SHA256 -Path $targetFiles[$relativePath]).Hash

            if ($sourceHash -ne $targetHash) {
                return $false
            }
        }
    }

    return $true
}

$availableSkills = @()
$skillNameCollisions = @{}
foreach ($root in $sourceRoots) {
    foreach ($n in (Get-SkillNames -Root $root)) {
        if ($availableSkills -contains $n) {
            $skillNameCollisions[$n] = $true
        } else {
            $availableSkills += $n
        }
    }
}

if ($skillNameCollisions.Count -gt 0) {
    $collided = ($skillNameCollisions.Keys | Sort-Object) -join ", "
    throw "Skill name collision across source roots: $collided. Rename or consolidate."
}

$skills = if ($SkillName -and $SkillName.Count -gt 0) {
    $SkillName
} else {
    $availableSkills
}

if (-not $skills) {
    throw "No skills found under any of: $($sourceRoots -join ', ')"
}

foreach ($name in $skills) {
    if ($availableSkills -notcontains $name) {
        throw "Unknown or unsafe skill name: $name"
    }
}

$repoRootPath = $repoRoot.Path

if (-not $ValidateOnly -and -not (Test-Path $resolvedWrapperRoot)) {
    New-Item -ItemType Directory -Path $resolvedWrapperRoot | Out-Null
}

foreach ($name in $skills) {
    $skillPath = Get-SkillSourcePath -Name $name -Roots $sourceRoots
    if (-not $skillPath) {
        throw "Skill source not found for: $name"
    }

    $skillRepoRelative = Get-SkillRelativeFromRepoRoot -SkillPath $skillPath -RepoRootPath $repoRootPath
    $targetPath = Join-Path $resolvedWrapperRoot $name

    if ($ValidateOnly) {
        $matches = Test-DirectoryMatchesSource -SourceDir $skillPath -TargetDir $targetPath -SkillRepoRelative $skillRepoRelative

        if (-not $matches) {
            throw "Claude skill copy is missing or out of sync: $targetPath"
        }

        Write-Host "Validated Claude skill copy $name -> $targetPath"
        continue
    }

    if (Test-Path $targetPath) {
        Remove-Item -Recurse -Force $targetPath
    }

    Copy-Item -Path $skillPath -Destination $resolvedWrapperRoot -Recurse
    $sourceFiles = Get-RelativeFileMap -Root $skillPath
    foreach ($relativePath in $sourceFiles.Keys) {
        if ($relativePath -notmatch '\.(md|ya?ml)$') {
            continue
        }

        $targetFile = Join-Path $targetPath ($relativePath -replace '/', '\')
        $targetContent = Get-ClaudeSkillCopyContent -SourceFile $sourceFiles[$relativePath] -SkillRepoRelative $skillRepoRelative -RelativePath $relativePath
        [System.IO.File]::WriteAllText($targetFile, $targetContent, [System.Text.UTF8Encoding]::new($false))
    }

    $writtenMatches = Test-DirectoryMatchesSource -SourceDir $skillPath -TargetDir $targetPath -SkillRepoRelative $skillRepoRelative
    if (-not $writtenMatches) {
        throw "Claude skill copy verification failed after sync: $targetPath"
    }

    Write-Host "Synced Claude skill copy $name -> $targetPath (source: $skillRepoRelative)"
}

if ($ValidateOnly) {
    Write-Host "Claude skill copy validation complete."
} else {
    Write-Host "Claude skill copy sync complete."
}
