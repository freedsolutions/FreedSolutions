param(
    [Parameter(ParameterSetName = 'Literal', Mandatory = $true)]
    [AllowEmptyString()]
    [string]$LiteralContent,

    [Parameter(ParameterSetName = 'SourceFile', Mandatory = $true)]
    [string]$SourceFile,

    [Parameter(Mandatory = $true)]
    [string]$DocSlug,

    [switch]$ExtractPageContent,

    [string]$Date = (Get-Date).ToString('yyyy-MM-dd'),

    [string]$OutputPath,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$notionWorkspaceHelperPath = Join-Path $PSScriptRoot 'notion-workspace-helpers.ps1'
if (-not (Test-Path -LiteralPath $notionWorkspaceHelperPath -PathType Leaf)) {
    throw "Required helper script not found: $notionWorkspaceHelperPath"
}

. $notionWorkspaceHelperPath

foreach ($requiredCommand in @('Resolve-RepoScopedPath', 'Get-NotionWorkspaceRepoRoot')) {
    if (-not (Get-Command -Name $requiredCommand -ErrorAction SilentlyContinue)) {
        throw ('Required helper command is unavailable after loading ' + $notionWorkspaceHelperPath + ': ' + $requiredCommand)
    }
}

function Test-IsChildPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,

        [Parameter(Mandatory = $true)]
        [string]$CandidatePath
    )

    $resolvedBase = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\', '/')
    $resolvedCandidate = [System.IO.Path]::GetFullPath($CandidatePath)
    $baseWithSeparator = $resolvedBase + [System.IO.Path]::DirectorySeparatorChar

    return (
        $resolvedCandidate.Equals($resolvedBase, [System.StringComparison]::OrdinalIgnoreCase) -or
        $resolvedCandidate.StartsWith($baseWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)
    )
}

function Get-DefaultOutputPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$DocSlug,

        [Parameter(Mandatory = $true)]
        [string]$Date
    )

    $relativePath = "ops/notion-workspace/tmp/notion-sync-remote-$Date-$DocSlug.md"
    return (Resolve-RepoScopedPath -Path $relativePath).FullPath
}

function Resolve-AllowedOutputPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $repoScratchRoot = (Resolve-RepoScopedPath -Path 'ops/notion-workspace/tmp').FullPath
    $tempRoot = [System.IO.Path]::GetTempPath()

    if (
        -not (Test-IsChildPath -BasePath $repoScratchRoot -CandidatePath $resolvedPath) -and
        -not (Test-IsChildPath -BasePath $tempRoot -CandidatePath $resolvedPath)
    ) {
        throw "OutputPath must stay inside ops/notion-workspace/tmp or the system temp directory: $resolvedPath"
    }

    if (
        $resolvedPath.Equals([System.IO.Path]::GetFullPath($repoScratchRoot), [System.StringComparison]::OrdinalIgnoreCase) -or
        $resolvedPath.Equals([System.IO.Path]::GetFullPath($tempRoot), [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "OutputPath must resolve to a file path, not the root of an allowed directory: $resolvedPath"
    }

    return $resolvedPath
}

function Assert-NoReparsePointsInParentChain {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $parentPath = Split-Path -Parent $resolvedPath
    if (-not $parentPath) {
        return
    }

    $rootPath = [System.IO.Path]::GetPathRoot($resolvedPath)
    if (-not $rootPath) {
        return
    }

    $segments = $parentPath.Substring($rootPath.Length).Split([char[]]@('\', '/'), [System.StringSplitOptions]::RemoveEmptyEntries)
    $cursor = $rootPath

    foreach ($segment in $segments) {
        $cursor = Join-Path $cursor $segment
        if (-not (Test-Path -LiteralPath $cursor)) {
            continue
        }

        $item = Get-Item -LiteralPath $cursor -Force
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            throw "OutputPath traverses a reparse point and must be rejected: $resolvedPath"
        }
    }
}

function Write-Bytes {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [byte[]]$Bytes
    )

    $directory = Split-Path -Parent $Path
    if ($directory -and -not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }

    [System.IO.File]::WriteAllBytes($Path, $Bytes)
}

function Remove-OneBoundaryLineBreak {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [ValidateSet('Start', 'End')]
        [string]$Side
    )

    if ($Side -eq 'Start') {
        if ($Text.StartsWith("`r`n", [System.StringComparison]::Ordinal)) {
            return $Text.Substring(2)
        }

        if ($Text.StartsWith("`n", [System.StringComparison]::Ordinal)) {
            return $Text.Substring(1)
        }

        return $Text
    }

    if ($Text.EndsWith("`r`n", [System.StringComparison]::Ordinal)) {
        return $Text.Substring(0, $Text.Length - 2)
    }

    if ($Text.EndsWith("`n", [System.StringComparison]::Ordinal)) {
        return $Text.Substring(0, $Text.Length - 1)
    }

    return $Text
}

function Get-ExtractedPageContent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $openTag = '<content>'
    $closeTag = '</content>'

    $startIndex = $Text.IndexOf($openTag, [System.StringComparison]::OrdinalIgnoreCase)
    if ($startIndex -lt 0) {
        throw 'The supplied fetch payload does not contain a <content> block.'
    }

    $closeIndex = $Text.IndexOf($closeTag, $startIndex + $openTag.Length, [System.StringComparison]::OrdinalIgnoreCase)
    if ($closeIndex -lt 0) {
        throw 'The supplied fetch payload does not contain a closing </content> block.'
    }

    $contentStart = $startIndex + $openTag.Length
    $contentLength = $closeIndex - $contentStart
    $content = $Text.Substring($contentStart, $contentLength)

    # Notion fetch wraps page bodies with one boundary line break after <content>
    # and before </content>. Remove at most one boundary break on each side so
    # intentional blank first/last lines in the page body remain intact.
    $content = Remove-OneBoundaryLineBreak -Text $content -Side Start
    $content = Remove-OneBoundaryLineBreak -Text $content -Side End

    return $content
}

if ($DocSlug -notmatch '^[a-z0-9][a-z0-9-]*$') {
    throw ('DocSlug must match ^[a-z0-9][a-z0-9-]*$: ' + $DocSlug)
}

if ($Date -notmatch '^\d{4}-\d{2}-\d{2}$') {
    throw "Date must be YYYY-MM-DD: $Date"
}

$finalOutputPath = if ($PSBoundParameters.ContainsKey('OutputPath')) {
    Resolve-AllowedOutputPath -Path $OutputPath
} else {
    Get-DefaultOutputPath -DocSlug $DocSlug -Date $Date
}

Assert-NoReparsePointsInParentChain -Path $finalOutputPath

if (Test-Path -LiteralPath $finalOutputPath) {
    $destinationItem = Get-Item -LiteralPath $finalOutputPath -Force
    if ($destinationItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw "OutputPath points to a reparse point and must be rejected: $finalOutputPath"
    }
}

if ((Test-Path -LiteralPath $finalOutputPath) -and -not $Force) {
    throw "Output path already exists. Re-run with -Force to overwrite: $finalOutputPath"
}

$bytes = switch ($PSCmdlet.ParameterSetName) {
    'Literal' {
        $text = if ($ExtractPageContent) {
            Get-ExtractedPageContent -Text $LiteralContent
        } else {
            $LiteralContent
        }

        [System.Text.UTF8Encoding]::new($false).GetBytes($text)
        break
    }
    'SourceFile' {
        $sourceFilePath = [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $SourceFile).Path)

        if ($ExtractPageContent) {
            $encoding = [System.Text.UTF8Encoding]::new($false, $true)
            $rawText = $encoding.GetString([System.IO.File]::ReadAllBytes($sourceFilePath))
            if ($rawText.Length -gt 0 -and $rawText[0] -eq [char]0xFEFF) {
                $rawText = $rawText.Substring(1)
            }
            $content = Get-ExtractedPageContent -Text $rawText
            [System.Text.UTF8Encoding]::new($false).GetBytes($content)
        } else {
            [System.IO.File]::ReadAllBytes($sourceFilePath)
        }

        break
    }
    default {
        throw "Unhandled parameter set: $($PSCmdlet.ParameterSetName)"
    }
}

Write-Bytes -Path $finalOutputPath -Bytes $bytes
Write-Output $finalOutputPath
