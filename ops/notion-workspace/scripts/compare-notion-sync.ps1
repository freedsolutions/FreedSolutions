param(
    [Parameter(Mandatory = $true)]
    [string]$LocalFile,

    [Parameter(Mandatory = $true)]
    [string]$RemoteFile
)

$ErrorActionPreference = 'Stop'

function Normalize-NotionSyncText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,

        [Parameter(Mandatory = $true)]
        [bool]$StripRepoOnlyPageId
    )

    $normalized = $Text -replace "`r`n?", "`n"
    $normalized = [regex]::Replace($normalized, "^\uFEFF", '')
    $normalized = $normalized.Replace([char]0x00A0, ' ')

    if ($StripRepoOnlyPageId) {
        $normalized = [regex]::Replace($normalized, '(?m)^\s*<!--\s*Notion Page ID:\s*.*?-->\s*\n?', '')
    }

    $normalized = $normalized -replace "`t", '  '
    $normalized = [regex]::Replace($normalized, '[ \t]+(?=\n)', '')
    $normalized = [regex]::Replace($normalized, "\n{3,}", "`n`n")

    return $normalized.Trim()
}

function Read-Utf8Text {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $encoding = [System.Text.UTF8Encoding]::new($false, $true)
    return $encoding.GetString($bytes)
}

function Get-FirstDiff {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Left,

        [Parameter(Mandatory = $true)]
        [string]$Right
    )

    $leftLines = $Left -split "`n"
    $rightLines = $Right -split "`n"
    $max = [Math]::Max($leftLines.Length, $rightLines.Length)

    for ($i = 0; $i -lt $max; $i++) {
        $leftLine = if ($i -lt $leftLines.Length) { $leftLines[$i] } else { '<missing>' }
        $rightLine = if ($i -lt $rightLines.Length) { $rightLines[$i] } else { '<missing>' }

        if ($leftLine -cne $rightLine) {
            return [pscustomobject]@{
                Line   = $i + 1
                Local  = $leftLine
                Remote = $rightLine
            }
        }
    }

    return $null
}

$localRaw = Read-Utf8Text -Path $LocalFile
$remoteRaw = Read-Utf8Text -Path $RemoteFile

if ($remoteRaw -match '<!--\s*Notion Page ID: .*?-->') {
    throw "Live content still contains the repo-only Notion Page ID comment."
}

$localNormalized = Normalize-NotionSyncText -Text $localRaw -StripRepoOnlyPageId $true
$remoteNormalized = Normalize-NotionSyncText -Text $remoteRaw -StripRepoOnlyPageId $false

if ($localNormalized -cne $remoteNormalized) {
    $diff = Get-FirstDiff -Left $localNormalized -Right $remoteNormalized
    $message = "Notion sync parity failed between '$LocalFile' and '$RemoteFile'."

    if ($null -ne $diff) {
        $message += " First difference at line $($diff.Line). Local: $($diff.Local) | Remote: $($diff.Remote)"
    }

    throw $message
}

Write-Output "Notion sync parity OK: $LocalFile <-> $RemoteFile"
