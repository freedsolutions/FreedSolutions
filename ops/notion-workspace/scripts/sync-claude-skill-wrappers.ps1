param(
    [string[]]$SkillName,
    [string]$WrapperRoot,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$workspaceRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$repoRoot = Resolve-Path (Join-Path (Join-Path $workspaceRoot "..") "..")
$sourceRoot = Join-Path $workspaceRoot "skills"

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

function Get-ClaudeSkillCopyContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceFile,

        [Parameter(Mandatory = $true)]
        [string]$SkillName,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $raw = Get-Content -Path $SourceFile -Raw
    $newline = if ($raw -match "`r`n") { "`r`n" } else { "`n" }
    $sourcePath = "ops/notion-workspace/skills/$SkillName/$RelativePath".Replace('\', '/')
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
        [string]$SkillName
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

        if ($relativePath -eq "SKILL.md") {
            $expectedContent = Get-ClaudeSkillCopyContent -SourceFile $sourceFiles[$relativePath] -SkillName $SkillName -RelativePath $relativePath
            $actualContent = Get-Content -Path $targetFiles[$relativePath] -Raw
            $normalizedExpected = $expectedContent -replace "\r\n", "`n"
            $normalizedActual = $actualContent -replace "\r\n", "`n"

            if ($normalizedExpected -ne $normalizedActual) {
                return $false
            }
        } elseif ($relativePath -match '\.(md|ya?ml)$') {
            $expectedContent = Get-ClaudeSkillCopyContent -SourceFile $sourceFiles[$relativePath] -SkillName $SkillName -RelativePath $relativePath
            $actualContent = Get-Content -Path $targetFiles[$relativePath] -Raw
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

$availableSkills = Get-SkillNames -Root $sourceRoot

$skills = if ($SkillName -and $SkillName.Count -gt 0) {
    $SkillName
} else {
    $availableSkills
}

if (-not $skills) {
    throw "No skills found under $sourceRoot"
}

foreach ($name in $skills) {
    if ($availableSkills -notcontains $name) {
        throw "Unknown or unsafe skill name: $name"
    }
}

if (-not $ValidateOnly -and -not (Test-Path $resolvedWrapperRoot)) {
    New-Item -ItemType Directory -Path $resolvedWrapperRoot | Out-Null
}

foreach ($name in $skills) {
    $skillPath = Join-Path $sourceRoot $name
    $skillFile = Join-Path $skillPath "SKILL.md"

    if (-not (Test-Path $skillFile)) {
        throw "Skill source not found: $skillFile"
    }

    $targetPath = Join-Path $resolvedWrapperRoot $name

    if ($ValidateOnly) {
        $matches = Test-DirectoryMatchesSource -SourceDir $skillPath -TargetDir $targetPath -SkillName $name

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
        $targetContent = Get-ClaudeSkillCopyContent -SourceFile $sourceFiles[$relativePath] -SkillName $name -RelativePath $relativePath
        [System.IO.File]::WriteAllText($targetFile, $targetContent, [System.Text.UTF8Encoding]::new($false))
    }

    $writtenMatches = Test-DirectoryMatchesSource -SourceDir $skillPath -TargetDir $targetPath -SkillName $name
    if (-not $writtenMatches) {
        throw "Claude skill copy verification failed after sync: $targetPath"
    }

    Write-Host "Synced Claude skill copy $name -> $targetPath"
}

if ($ValidateOnly) {
    Write-Host "Claude skill copy validation complete."
} else {
    Write-Host "Claude skill copy sync complete."
}
