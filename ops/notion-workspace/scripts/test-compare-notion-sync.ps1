param()

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$compareScript = Join-Path $scriptDir 'compare-notion-sync.ps1'
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("notion-sync-test-" + [guid]::NewGuid().ToString())

New-Item -ItemType Directory -Path $tempDir | Out-Null

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content,

        [Parameter(Mandatory = $false)]
        [bool]$WithBom = $false
    )

    $encoding = [System.Text.UTF8Encoding]::new($WithBom)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Expect-Pass {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Local,

        [Parameter(Mandatory = $true)]
        [string]$Remote
    )

    try {
        & $compareScript -LocalFile $Local -RemoteFile $Remote | Out-Null
    }
    catch {
        throw "Expected pass for '$Name' but failed: $($_.Exception.Message)"
    }
}

function Expect-Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Local,

        [Parameter(Mandatory = $true)]
        [string]$Remote
    )

    $failed = $false

    try {
        & $compareScript -LocalFile $Local -RemoteFile $Remote | Out-Null
    }
    catch {
        $failed = $true
    }

    if (-not $failed) {
        throw "Expected failure for '$Name' but the comparison passed."
    }
}

try {
    $local1 = Join-Path $tempDir 'local-lf.md'
    $remote1 = Join-Path $tempDir 'remote-crlf.md'
    Write-Utf8File -Path $local1 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote1 -Content "# Title`r`nBody`r`n"
    Expect-Pass -Name 'line-ending-normalization' -Local $local1 -Remote $remote1

    $local2 = Join-Path $tempDir 'local-comment.md'
    $remote2 = Join-Path $tempDir 'remote-comment.md'
    Write-Utf8File -Path $local2 -Content "<!-- Notion Page ID: 123 -->`n`n# Title`nBody`n" -WithBom $true
    Write-Utf8File -Path $remote2 -Content "# Title`nBody`n"
    Expect-Pass -Name 'repo-only-comment-strip' -Local $local2 -Remote $remote2

    $local2b = Join-Path $tempDir 'local-comment-tight.md'
    $remote2b = Join-Path $tempDir 'remote-comment-tight.md'
    Write-Utf8File -Path $local2b -Content "<!-- Notion Page ID: 123-->`n# Title`nBody`n"
    Write-Utf8File -Path $remote2b -Content "# Title`nBody`n"
    Expect-Pass -Name 'repo-only-comment-strip-tight-close' -Local $local2b -Remote $remote2b

    $local3 = Join-Path $tempDir 'local-case.md'
    $remote3 = Join-Path $tempDir 'remote-case.md'
    Write-Utf8File -Path $local3 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote3 -Content "# Title`nbody`n"
    Expect-Fail -Name 'case-sensitive-diff' -Local $local3 -Remote $remote3

    $local4 = Join-Path $tempDir 'local-remote-comment.md'
    $remote4 = Join-Path $tempDir 'remote-remote-comment.md'
    Write-Utf8File -Path $local4 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote4 -Content "<!-- Notion Page ID: 123 -->`n# Title`nBody`n"
    Expect-Fail -Name 'live-comment-detection' -Local $local4 -Remote $remote4

    $local5 = Join-Path $tempDir 'local-whitespace.md'
    $remote5 = Join-Path $tempDir 'remote-whitespace.md'
    Write-Utf8File -Path $local5 -Content "# Title`n`tBody  `n`n`nTail`n"
    Write-Utf8File -Path $remote5 -Content "# Title`n  Body`n`nTail`n"
    Expect-Pass -Name 'tab-trailing-space-normalization' -Local $local5 -Remote $remote5

    $local5b = Join-Path $tempDir 'local-blank-lines.md'
    $remote5b = Join-Path $tempDir 'remote-blank-lines.md'
    Write-Utf8File -Path $local5b -Content "# Title`n`n`n`nBody`n"
    Write-Utf8File -Path $remote5b -Content "# Title`n`nBody`n"
    Expect-Pass -Name 'blank-line-normalization' -Local $local5b -Remote $remote5b

    $local6 = Join-Path $tempDir 'local-remote-bom.md'
    $remote6 = Join-Path $tempDir 'remote-remote-bom.md'
    Write-Utf8File -Path $local6 -Content "# Title`nBody`n"
    Write-Utf8File -Path $remote6 -Content "# Title`nBody`n" -WithBom $true
    Expect-Pass -Name 'remote-bom-normalization' -Local $local6 -Remote $remote6

    $local7 = Join-Path $tempDir 'local-unicode.md'
    $remote7 = Join-Path $tempDir 'remote-unicode.md'
    Write-Utf8File -Path $local7 -Content "# Title`nCafe - launch 🚀`n"
    Write-Utf8File -Path $remote7 -Content "# Title`nCafe - launch 🚀`n"
    Expect-Pass -Name 'unicode-utf8-read' -Local $local7 -Remote $remote7

    $local8 = Join-Path $tempDir 'local-nbsp.md'
    $remote8 = Join-Path $tempDir 'remote-nbsp.md'
    Write-Utf8File -Path $local8 -Content "# Title`nAlpha Beta`n"
    Write-Utf8File -Path $remote8 -Content ("# Title`nAlpha" + [char]0x00A0 + "Beta`n")
    Expect-Pass -Name 'nbsp-normalization' -Local $local8 -Remote $remote8

    Write-Output 'compare-notion-sync tests passed.'
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
}
